import binascii
import contextlib
import time
from base64 import b64decode, b64encode
from os import urandom
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional

from orjson import OPT_SERIALIZE_NUMPY, dumps
from orjson.orjson import loads
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
from starlette.requests import HTTPConnection
from typing_extensions import Literal

from starlite.datastructures import Cookie
from starlite.exceptions import MissingDependencyException
from starlite.middleware.base import MiddlewareProtocol
from starlite.response import Response

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as e:
    raise MissingDependencyException("cryptography is not installed") from e

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

ONE_DAY_IN_SECONDS = 60 * 60 * 24
NONCE_SIZE = 12
CHUNK_SIZE = 4096 - 512


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
    secure: Optional[bool] = None
    """Https is required for the cookie."""
    httponly: Optional[bool] = None
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
        if len(value.get_secret_value()) not in [16, 24, 32]:
            raise ValueError("secret length must be 16 (128 bit), 24 (192 bit) or 32 (256 bit)")
        return value


class SessionMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: "ASGIApp",
        config: SessionCookieConfig,
    ):
        """Starlite SessionMiddleware.

        Args:
            app: The 'next' ASGI app to call.
            config: SessionCookieConfig instance.
        """
        super().__init__(app)
        self.app = app
        self.config = config
        self.aesgcm = AESGCM(config.secret.get_secret_value())

    def dump_data(self, data: Any) -> List[bytes]:
        """Given orjson serializable data, including pydantic models and numpy
        types, dump it into a bytes string, encrypt, encode and split it into
        chunks of the desirable size.

        Args:
            data: Data to serialize, encrypt, encode and chunk.

        Notes:
            - The returned list is composed of a chunks of a single base64 encoded
                string that is encrypted using AES-CGM.

        Returns:
            List of encoded bytes string of a maximum length equal to the 'CHUNK_SIZE' constant.
        """
        serialized = dumps(data, default=Response.serializer, option=OPT_SERIALIZE_NUMPY)
        associated_data = dumps({"timestamp": round(time.time()), "max_age": self.config.max_age})
        nonce = urandom(NONCE_SIZE)
        encrypted = self.aesgcm.encrypt(nonce, serialized, associated_data=associated_data)
        encoded = b64encode(nonce + encrypted + b"associated_data=" + associated_data)
        return [encoded[i : i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]

    @staticmethod
    def _validate_session(associated_data: dict) -> bool:
        """Verifies the validity of the session.

        Args:
            associated_data: A dictionary contains the timestamp of the AEAD Tag and max-age of the session.

        Returns:
            bool: True if the session is NOT expired else False.
        """
        timestamp = associated_data["timestamp"]
        max_age = associated_data["max_age"]
        if timestamp + max_age >= int(time.time()):
            return True
        return False

    def load_data(self, data: List[bytes]) -> Any:
        """Given a list of strings, decodes them into the session object.

        Args:
            data: A list of strings derived from the request's session cookie(s).

        Returns:
            A deserialized session value.
        """
        decoded = b64decode(b"".join(data))
        nonce = decoded[:NONCE_SIZE]

        associated_data = None
        associated_data_footer = decoded.find(b"associated_data=")
        if associated_data_footer != -1:
            associated_data = decoded[associated_data_footer:].replace(b"associated_data=", b"")

        encrypted_session = decoded[NONCE_SIZE:associated_data_footer]
        decrypted = self.aesgcm.decrypt(nonce, encrypted_session, associated_data=associated_data)

        session_validation = self._validate_session(associated_data=loads(associated_data))
        if session_validation is False:
            return {}
        return loads(decrypted)

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
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                data = self.dump_data(scope.get("session"))
                cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "key"})
                for i, datum in enumerate(data, start=0):
                    headers.append(
                        "Set-Cookie",
                        Cookie(value=datum.decode("utf-8"), key=f"{self.config.key}-{i}", **cookie_params)
                        .to_header()
                        .replace("Set-Cookie: ", ""),
                    )
                # Cookies with the same key overwrite the earlier cookie with that key. To expire earlier session
                # cookies, first check how many session cookies will not be overwritten in this upcoming response. If
                # leftover cookies are greater than or equal to 1, that means older session cookies have to be expired
                # and their names are in cookie_keys.
                cookies_left = len(cookie_keys) - len(data)
                if cookies_left >= 1:
                    cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "max_age", "key"})
                    for cookie_key in cookie_keys[len(data) :]:
                        headers.append(
                            "Set-Cookie",
                            Cookie(value="null", key=cookie_key, expires=0, **cookie_params)
                            .to_header()
                            .replace("Set-Cookie: ", ""),
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
            connection = HTTPConnection(scope)
            cookie_keys = sorted(key for key in connection.cookies if self.config.key in key)
            if cookie_keys:
                with contextlib.suppress(KeyError):
                    data = [connection.cookies[key].encode("utf-8") for key in cookie_keys]
                with contextlib.suppress(InvalidTag, binascii.Error):
                    scope["session"] = self.load_data(data)
            await self.app(scope, receive, self.create_send_wrapper(scope, send, cookie_keys))
        else:
            await self.app(scope, receive, send)
