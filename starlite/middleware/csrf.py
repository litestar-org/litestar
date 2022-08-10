import hashlib
import hmac
import secrets
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, Any, Optional

from starlette.datastructures import MutableHeaders

from starlite.connection import Request
from starlite.exceptions import PermissionDeniedException
from starlite.types import MiddlewareProtocol

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from starlite.config import CSRFConfig

CSRF_SECRET_BYTES = 32
CSRF_SECRET_LENGTH = CSRF_SECRET_BYTES * 2


class CSRFMiddleware(MiddlewareProtocol):
    """CSRF middleware for Starlite

    Prevent CSRF attacks by setting a CSRF cookie with a token and verifying it in request headers.
    """

    def __init__(
        self,
        app: "ASGIApp",
        config: "CSRFConfig",
    ):
        super().__init__(app)
        self.app = app
        self.config = config

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request[Any, Any](scope=scope)
        csrf_cookie = request.cookies.get(self.config.cookie_name)
        existing_csrf_token = request.headers.get(self.config.header_name)

        send_callable_to_use = send

        if request.method not in self.config.safe_methods:
            if not self._csrf_tokens_match(existing_csrf_token, csrf_cookie):
                raise PermissionDeniedException("CSRF token verification failed")
        else:

            async def send_wrapper(message: "Message") -> None:
                if csrf_cookie is None and message["type"] == "http.response.start":
                    message.setdefault("headers", [])
                    headers = MutableHeaders(scope=message)
                    if "set-cookie" not in headers:
                        cookie: SimpleCookie = SimpleCookie()
                        cookie[self.config.cookie_name] = self._generate_csrf_token()
                        cookie[self.config.cookie_name]["path"] = self.config.cookie_path
                        cookie[self.config.cookie_name]["secure"] = self.config.cookie_secure
                        cookie[self.config.cookie_name]["httponly"] = self.config.cookie_httponly
                        cookie[self.config.cookie_name]["samesite"] = self.config.cookie_samesite
                        if self.config.cookie_domain is not None:
                            cookie[self.config.cookie_name]["domain"] = self.config.cookie_domain
                        headers.append("set-cookie", cookie.output(header="").strip())
                await send(message)

            send_callable_to_use = send_wrapper

        await self.app(scope, receive, send_callable_to_use)

    def _generate_csrf_hash(self, token: str) -> str:
        """Generate an HMAC that signs the CSRF token"""
        return hmac.new(self.config.secret.encode(), token.encode(), hashlib.sha256).hexdigest()

    def _generate_csrf_token(self) -> str:
        """Generate a CSRF token that includes a randomly generated string signed by an HMAC"""
        token = secrets.token_hex(CSRF_SECRET_BYTES)
        token_hash = self._generate_csrf_hash(token)
        return token + token_hash

    def _decode_csrf_token(self, token: str) -> Optional[str]:
        """Decode a CSRF token and validate its HMAC"""
        if len(token) < CSRF_SECRET_LENGTH + 1:
            return None

        ts = token[:CSRF_SECRET_LENGTH]
        existing_hash = token[CSRF_SECRET_LENGTH:]
        expected_hash = self._generate_csrf_hash(ts)
        if not secrets.compare_digest(existing_hash, expected_hash):
            return None

        return ts

    def _csrf_tokens_match(self, request_csrf_token: Optional[str], cookie_csrf_token: Optional[str]) -> bool:
        """Takes the CSRF tokens from the request and the cookie and verifies both are valid and identical"""
        if not (request_csrf_token and cookie_csrf_token):
            return False

        decoded_request_token = self._decode_csrf_token(request_csrf_token)
        decoded_cookie_token = self._decode_csrf_token(cookie_csrf_token)
        if decoded_request_token is None or decoded_cookie_token is None:
            return False

        return secrets.compare_digest(decoded_request_token, decoded_cookie_token)
