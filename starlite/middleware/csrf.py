import hashlib
import hmac
import secrets
from http.cookies import SimpleCookie
from typing import Optional

from starlette.datastructures import MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from starlite.config import CSRFConfig
from starlite.connection import Request
from starlite.types import MiddlewareProtocol

CSRF_SECRET_BYTES = 32
CSRF_SECRET_LENGTH = CSRF_SECRET_BYTES * 2


class BadSignature(Exception):
    pass


class CSRFMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: ASGIApp,
        config: CSRFConfig,
    ):
        super().__init__(app)
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope=scope)
        csrf_cookie = request.cookies.get(self.config.cookie_name)
        existing_csrf_token = request.headers.get(self.config.header_name)

        my_send = send

        if request.method not in self.config.safe_methods:
            if not self._csrf_tokens_match(existing_csrf_token, csrf_cookie):
                response = self._get_error_response()
                await response(scope, receive, send)
                return
        else:

            async def send_wrapper(message: Message):
                if csrf_cookie is None and message["type"] == "http.response.start":
                    message.setdefault("headers", [])
                    headers = MutableHeaders(scope=message)
                    if "set-cookie" not in headers:
                        cookie = SimpleCookie()
                        cookie[self.config.cookie_name] = self._generate_csrf_token()
                        cookie[self.config.cookie_name]["path"] = self.config.cookie_path
                        cookie[self.config.cookie_name]["secure"] = self.config.cookie_secure
                        cookie[self.config.cookie_name]["httponly"] = self.config.cookie_httponly
                        cookie[self.config.cookie_name]["samesite"] = self.config.cookie_samesite
                        if self.config.cookie_domain is not None:
                            cookie[self.config.cookie_name]["domain"] = self.config.cookie_domain
                        headers.append("set-cookie", cookie.output(header="").strip())
                await send(message)

            my_send = send_wrapper

        await self.app(scope, receive, my_send)

    def _generate_csrf_hash(self, token: str) -> str:
        return hmac.new(self.config.secret.encode(), token.encode(), hashlib.sha256).hexdigest()

    def _generate_csrf_token(self) -> str:
        token = secrets.token_hex(CSRF_SECRET_BYTES)
        token_hash = self._generate_csrf_hash(token)
        return token + token_hash

    def _decode_csrf_token(self, token: str) -> str:
        if len(token) < CSRF_SECRET_LENGTH + 1:
            raise BadSignature

        ts = token[:CSRF_SECRET_LENGTH]
        existing_hash = token[CSRF_SECRET_LENGTH:]
        expected_hash = self._generate_csrf_hash(ts)
        if not secrets.compare_digest(existing_hash, expected_hash):
            raise BadSignature

        return ts

    def _csrf_tokens_match(self, request_csrf_token: Optional[str], cookie_csrf_token: Optional[str]) -> bool:
        if not (request_csrf_token and cookie_csrf_token):
            return False
        try:
            decoded_request_token = self._decode_csrf_token(request_csrf_token)
            decoded_cookie_token = self._decode_csrf_token(cookie_csrf_token)
            return secrets.compare_digest(decoded_request_token, decoded_cookie_token)
        except BadSignature:
            return False

    @classmethod
    def _get_error_response(cls) -> PlainTextResponse:
        return PlainTextResponse(content="CSRF token verification failed", status_code=403)
