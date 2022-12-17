import binascii
import contextlib
import re
import time
from base64 import b64decode, b64encode
from os import urandom
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import SecretBytes, validator

from starlite.datastructures import MutableScopeHeaders
from starlite.datastructures.cookie import Cookie
from starlite.exceptions import MissingDependencyException
from starlite.types import Empty
from starlite.utils.serialization import decode_json, encode_json

from .base import BaseBackendConfig, BaseSessionBackend

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as e:
    raise MissingDependencyException("cryptography is not installed") from e

if TYPE_CHECKING:
    from starlite.connection import ASGIConnection
    from starlite.types import Message, Scope, ScopeSession

NONCE_SIZE = 12
CHUNK_SIZE = 4096 - 64
AAD = b"additional_authenticated_data="


class CookieBackend(BaseSessionBackend["CookieBackendConfig"]):
    """Cookie backend for SessionMiddleware."""

    __slots__ = ("aesgcm", "cookie_re")

    def __init__(self, config: "CookieBackendConfig") -> None:
        """Initialize `CookieBackend`.

        Args:
            config: SessionCookieConfig instance.
        """
        super().__init__(config)
        self.aesgcm = AESGCM(config.secret.get_secret_value())
        self.cookie_re = re.compile(rf"{self.config.key}(?:-\d+)?")

    def dump_data(self, data: Any, scope: Optional["Scope"] = None) -> List[bytes]:
        """Given serializable data, including pydantic models and numpy types, dump it into a bytes string, encrypt,
        encode and split it into chunks of the desirable size.

        Args:
            data: Data to serialize, encrypt, encode and chunk.
            scope: The ASGI connection scope.

        Notes:
            - The returned list is composed of a chunks of a single base64 encoded
            string that is encrypted using AES-CGM.

        Returns:
            List of encoded bytes string of a maximum length equal to the 'CHUNK_SIZE' constant.
        """
        serialized = self.serlialize_data(data, scope)
        associated_data = encode_json({"expires_at": round(time.time()) + self.config.max_age})
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
        if associated_data and decode_json(associated_data)["expires_at"] > round(time.time()):
            encrypted_session = decoded[NONCE_SIZE:aad_starts_from]
            decrypted = self.aesgcm.decrypt(nonce, encrypted_session, associated_data=associated_data)
            return self.deserialize_data(decrypted)
        return {}

    def get_cookie_keys(self, connection: "ASGIConnection") -> List[str]:
        """Return a list of cookie-keys from the connection if they match the session-cookie pattern.

        Args:
            connection: An ASGIConnection instance

        Returns:
            A list of session-cookie keys
        """
        return sorted(key for key in connection.cookies if self.cookie_re.fullmatch(key))

    def _create_session_cookies(
        self, data: List[bytes], cookie_params: Optional[Dict[str, Any]] = None
    ) -> List[Cookie]:
        """Create a list of cookies containing the session data."""
        if cookie_params is None:
            cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "key"})
        return [
            Cookie(value=datum.decode("utf-8"), key=f"{self.config.key}-{i}", **cookie_params)
            for i, datum in enumerate(data)
        ]

    async def store_in_message(
        self, scope_session: "ScopeSession", message: "Message", connection: "ASGIConnection"
    ) -> None:
        """Store data from `scope_session` in `Message` in the form of cookies. If the contents of `scope_session` are
        too large to fit a single cookie, it will be split across several cookies, following the naming scheme of
        `<cookie key>-<n>`. If the session is empty or shrinks, cookies will be cleared by setting their value to `null`

        Args:
            scope_session: Current session to store
            message: Outgoing send-message
            connection: Originating ASGIConnection containing the scope

        Returns:
            None
        """

        scope = connection.scope
        headers = MutableScopeHeaders.from_message(message)
        cookie_keys = self.get_cookie_keys(connection)

        if scope_session and scope_session is not Empty:
            data = self.dump_data(scope_session, scope=scope)
            cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "key"})
            for cookie in self._create_session_cookies(data, cookie_params):
                headers.add("Set-Cookie", cookie.to_header(header=""))
            # Cookies with the same key overwrite the earlier cookie with that key. To expire earlier session
            # cookies, first check how many session cookies will not be overwritten in this upcoming response.
            # If leftover cookies are greater than or equal to 1, that means older session cookies have to be
            # expired and their names are in cookie_keys.
            cookies_to_clear = cookie_keys[len(data) :] if len(cookie_keys) - len(data) > 0 else []
        else:
            cookies_to_clear = cookie_keys

        for cookie_key in cookies_to_clear:
            cookie_params = self.config.dict(exclude_none=True, exclude={"secret", "max_age", "key"})
            headers.add(
                "Set-Cookie",
                Cookie(value="null", key=cookie_key, expires=0, **cookie_params).to_header(header=""),
            )

    async def load_from_connection(self, connection: "ASGIConnection") -> Dict[str, Any]:
        """Load session data from a connection's session-cookies and return it as a dictionary.

        Args:
            connection: Originating ASGIConnection

        Returns:
            The session data
        """
        cookie_keys = self.get_cookie_keys(connection)
        if cookie_keys:
            data = [connection.cookies[key].encode("utf-8") for key in cookie_keys]
            # If these exceptions occur, the session must remain empty so do nothing.
            with contextlib.suppress(InvalidTag, binascii.Error):
                return self.load_data(data)
        return {}


class CookieBackendConfig(BaseBackendConfig):
    """Configuration for [SessionMiddleware] middleware."""

    _backend_class: Type[CookieBackend] = CookieBackend

    secret: SecretBytes
    """A secret key to use for generating an encryption key.

    Must have a length of 16 (128 bits), 24 (192 bits) or 32 (256 bits) characters.
    """

    @validator("secret", always=True)
    def validate_secret(cls, value: SecretBytes) -> SecretBytes:  # pylint: disable=no-self-argument
        """Ensure that the 'secret' value is 128, 192 or 256 bits.

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
