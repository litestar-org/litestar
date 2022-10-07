import binascii
import contextlib
import time
from base64 import b64decode, b64encode
from os import urandom
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from orjson import OPT_SERIALIZE_NUMPY, dumps, loads
from pydantic import (
    BaseConfig,
    BaseModel,
    SecretBytes,
    conint,
    conlist,
    constr,
    validator,
)
from starlette.datastructures import MutableHeaders
from typing_extensions import Literal

from starlite.connection import ASGIConnection
from starlite.datastructures.cookie import Cookie
from starlite.exceptions import MissingDependencyException
from starlite.middleware.base import DefineMiddleware, MiddlewareProtocol
from starlite.utils import get_serializer_from_scope
from starlite.utils.serialization import default_serializer

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as e:
    raise MissingDependencyException("cryptography is not installed") from e

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Message, Receive, Scope, Send


ONE_DAY_IN_SECONDS = 60 * 60 * 24
NONCE_SIZE = 12
CHUNK_SIZE = 4096 - 64
AAD = b"additional_authenticated_data="


class SessionCookieConfig(BaseModel):
    """Configuration for Session middleware."""

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    secret: SecretBytes
    """
    A secret key to use for generating an encryption key.
    Must have a length of 16 (128 bits), 24 (192 bits) or 32 (256 bits) characters.
    """
    key: constr(min_length=1, max_length=256) = "session"  # type: ignore[valid-type]
    """
    Key to use for the cookie inside the header,
    e.g. `session=<data>` where 'session' is the cookie key and <data> is the session data.

    Notes:
        - If a session cookie exceeds 4KB in size it is split. In this case the key will be of the format
            'session-{segment number}'.
    """
    max_age: conint(ge=1) = ONE_DAY_IN_SECONDS * 14  # type: ignore[valid-type]
    """Maximal age of the cookie before its invalidated."""
    scopes: conlist(Literal["http", "websocket"], min_items=1, max_items=2) = ["http", "websocket"]  # type: ignore[valid-type]
    """Scopes for the middleware - options are 'http' and 'websocket' with the default being both"""
    path: str = "/"
    """Path fragment that must exist in the request url for the cookie to be valid. Defaults to '/'."""
    domain: Optional[str] = None
    """Domain for which the cookie is valid."""
    secure: bool = False
    """Https is required for the cookie."""
    httponly: bool = True
    """Forbids javascript to access the cookie via 'Document.cookie'."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    """Controls whether or not a cookie is sent with cross-site requests. Defaults to 'lax'."""

    @validator("secret", always=True)
    def validate_secret(cls, value: SecretBytes) -> SecretBytes:  # pylint: disable=no-self-argument
        """Ensures that the 'secret' value is 128, 192 or 256 bits.

        Args:
            value: A bytes string.

        Raises:
            ValueError: if the bytes string is of incorrect length.

        Returns:
            A bytes string.
        """
        if len(value.get_secret_value()) not in {16, 24, 32}:
            raise ValueError("secret length must be 16 (128 bit), 24 (192 bit) or 32 (256 bit)")
        return value

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one
        of the application layers.

        Examples:

            ```python
            from os import urandom

            from starlite import Starlite, Request, get
            from starlite.middleware.session import SessionCookieConfig

            session_config = SessionCookieConfig(secret=urandom(16))


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[session_config.middleware])
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(SessionMiddleware, config=self)


class SessionMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: "ASGIApp",
        config: SessionCookieConfig,
    ) -> None:
        """Starlite SessionMiddleware.

        Args:
            app: The 'next' ASGI app to call.
            config: SessionCookieConfig instance.
        """
        self.app = app
        self.config = config
        self.aesgcm = AESGCM(config.secret.get_secret_value())

    def dump_data(self, data: Any, scope: Optional["Scope"] = None) -> List[bytes]:
        """Given orjson serializable data, including pydantic models and numpy
        types, dump it into a bytes string, encrypt, encode and split it into
        chunks of the desirable size.

        Args:
            data: Data to serialize, encrypt, encode and chunk.
            scope: The ASGI connection scope.

        Notes:
            - The returned list is composed of a chunks of a single base64 encoded
                string that is encrypted using AES-CGM.

        Returns:
            List of encoded bytes string of a maximum length equal to the 'CHUNK_SIZE' constant.
        """
        serializer = (get_serializer_from_scope(scope) if scope else None) or default_serializer
        serialized = dumps(data, default=serializer, option=OPT_SERIALIZE_NUMPY)
        associated_data = dumps({"expires_at": round(time.time()) + self.config.max_age})
        nonce = urandom(NONCE_SIZE)
        encrypted = self.aesgcm.encrypt(nonce, serialized, associated_data=associated_data)
        encoded = b64encode(nonce + encrypted + AAD + associated_data)
        return [encoded[i : i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]

    def load_data(self, data: List[bytes]) -> Dict[str, Any]:
        """Given a list of strings, decodes them into the session object.

        Args:
            data: A list of strings derived from the request's session cookie(s).

        Returns:
            A deserialized session value.
        """
        decoded = b64decode(b"".join(data))
        nonce = decoded[:NONCE_SIZE]
        aad_starts_from = decoded.find(AAD)
        associated_data = decoded[aad_starts_from:].replace(AAD, b"") if aad_starts_from != -1 else None
        if associated_data and loads(associated_data)["expires_at"] > round(time.time()):
            encrypted_session = decoded[NONCE_SIZE:aad_starts_from]
            decrypted = self.aesgcm.decrypt(nonce, encrypted_session, associated_data=associated_data)
            return cast("Dict[str, Any]", loads(decrypted))
        return {}

    def create_send_wrapper(
        self, scope: "Scope", send: "Send", cookie_keys: List[str]
    ) -> Callable[["Message"], Awaitable[None]]:
        """
        Creates a wrapper for the ASGI send function, which handles setting the cookies on the outgoing response.
        Args:
            scope: The ASGI connection scope.
            send: The ASGI send function.
            cookie_keys: Session cookie keys that are sent in the current request. It is required to expire all session
                cookies from the current request and are replaced with new cookies in the upcoming response.

        Returns:
            None.
        """

        async def wrapped_send(message: "Message") -> None:
            """A wrapper around the send function, declared in local scope to
            use closure values.

            Args:
                message: An ASGI message.

            Returns:
                None
            """
            if message["type"] != "http.response.start":
                await send(message)
                return

            headers = MutableHeaders(scope=message)
            scope_session = scope.get("session")

            if scope_session:
                data = self.dump_data(scope_session, scope=scope)
                cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "key"})
                for i, datum in enumerate(data, start=0):
                    headers.append(
                        "Set-Cookie",
                        Cookie(value=datum.decode("utf-8"), key=f"{self.config.key}-{i}", **cookie_params).to_header(
                            header=""
                        ),
                    )
                # Cookies with the same key overwrite the earlier cookie with that key. To expire earlier session
                # cookies, first check how many session cookies will not be overwritten in this upcoming response.
                # If leftover cookies are greater than or equal to 1, that means older session cookies have to be
                # expired and their names are in cookie_keys.
                cookies_to_clear = cookie_keys[len(data) :] if len(cookie_keys) - len(data) > 0 else []
            else:
                cookies_to_clear = cookie_keys

            for cookie_key in cookies_to_clear:
                cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "max_age", "key"})
                headers.append(
                    "Set-Cookie",
                    Cookie(value="null", key=cookie_key, expires=0, **cookie_params).to_header(header=""),
                )

            await send(message)

        return wrapped_send

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if scope["type"] in self.config.scopes:
            scope.setdefault("session", {})
            connection = ASGIConnection[Any, Any, Any](scope)
            cookie_keys = sorted(key for key in connection.cookies if self.config.key in key)
            if cookie_keys:
                data = [connection.cookies[key].encode("utf-8") for key in cookie_keys]
                # If these exceptions occur, the session must remain empty so do nothing.
                with contextlib.suppress(InvalidTag, binascii.Error):
                    scope["session"] = self.load_data(data)
            await self.app(scope, receive, self.create_send_wrapper(scope, send, cookie_keys))
        else:
            await self.app(scope, receive, send)
