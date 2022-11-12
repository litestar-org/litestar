import secrets
from typing import TYPE_CHECKING, Any, Optional

from starlite.datastructures import MutableScopeHeaders
from starlite.datastructures.cookie import Cookie
from starlite.enums import RequestEncodingType, ScopeType
from starlite.exceptions import PermissionDeniedException
from starlite.middleware.base import MiddlewareProtocol
from starlite.middleware.utils import (
    build_exclude_path_pattern,
    should_bypass_middleware,
)
from starlite.utils.csrf import (
    CSRF_SECRET_BYTES,
    generate_csrf_hash,
    generate_csrf_token,
)

if TYPE_CHECKING:
    from starlite.config import CSRFConfig
    from starlite.connection import Request
    from starlite.types import (
        ASGIApp,
        HTTPSendMessage,
        Message,
        Receive,
        Scope,
        Scopes,
        Send,
    )

CSRF_SECRET_LENGTH = CSRF_SECRET_BYTES * 2


class CSRFMiddleware(MiddlewareProtocol):
    """CSRF Middleware class.

    This Middleware protects against attacks by setting a CSRF cookie with a token and verifying it in request headers.
    """

    scopes: "Scopes" = {ScopeType.HTTP}

    def __init__(self, app: "ASGIApp", config: "CSRFConfig") -> None:
        """Initialize `CSRFMiddleware`.

        Args:
            app: The 'next' ASGI app to call.
            config: The CSRFConfig instance.
        """
        self.app = app
        self.config = config
        self.exclude = build_exclude_path_pattern(exclude=config.exclude)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        request: "Request[Any, Any]" = scope["app"].request_class(scope=scope, receive=receive)
        content_type, _ = request.content_type
        csrf_cookie = request.cookies.get(self.config.cookie_name)
        existing_csrf_token = request.headers.get(self.config.header_name)

        if not existing_csrf_token and content_type in {
            RequestEncodingType.URL_ENCODED,
            RequestEncodingType.MULTI_PART,
        }:
            form = await request.form()
            existing_csrf_token = form.get("_csrf_token", None)

        if request.method in self.config.safe_methods or should_bypass_middleware(
            scope=scope,
            scopes=self.scopes,
            exclude_opt_key=self.config.exclude_from_csrf_key,
            exclude_path_pattern=self.exclude,
        ):
            token = scope["_csrf_token"] = csrf_cookie or generate_csrf_token(secret=self.config.secret)  # type: ignore
            await self.app(scope, receive, self.create_send_wrapper(send=send, csrf_cookie=csrf_cookie, token=token))
        elif self._csrf_tokens_match(existing_csrf_token, csrf_cookie):
            scope["_csrf_token"] = existing_csrf_token  # type: ignore
            await self.app(scope, receive, send)
        else:
            raise PermissionDeniedException("CSRF token verification failed")

    def create_send_wrapper(self, send: "Send", token: str, csrf_cookie: Optional[str]) -> "Send":
        """Wrap `send` to handle CSRF validation.

        Args:
            token: The CSRF token.
            send: The ASGI send function.
            csrf_cookie: CSRF cookie.

        Returns:
            An ASGI send function.
        """

        async def send_wrapper(message: "Message") -> None:
            """Send function that wraps the original send to inject a cookie.

            Args:
                message: An ASGI 'Message'

            Returns:
                None
            """
            if csrf_cookie is None and message["type"] == "http.response.start":
                message.setdefault("headers", [])
                self._set_cookie_if_needed(message=message, token=token)
            await send(message)

        return send_wrapper

    def _set_cookie_if_needed(self, message: "HTTPSendMessage", token: str) -> None:
        headers = MutableScopeHeaders.from_message(message)
        cookie = Cookie(
            key=self.config.cookie_name,
            value=token,
            path=self.config.cookie_path,
            secure=self.config.cookie_secure,
            httponly=self.config.cookie_httponly,
            samesite=self.config.cookie_samesite,
            domain=self.config.cookie_domain,
        )
        headers.add("set-cookie", cookie.to_header(header=""))

    def _decode_csrf_token(self, token: str) -> Optional[str]:
        """Decode a CSRF token and validate its HMAC."""
        if len(token) < CSRF_SECRET_LENGTH + 1:
            return None

        token_secret = token[:CSRF_SECRET_LENGTH]
        existing_hash = token[CSRF_SECRET_LENGTH:]
        expected_hash = generate_csrf_hash(token=token_secret, secret=self.config.secret)
        if not secrets.compare_digest(existing_hash, expected_hash):
            return None

        return token_secret

    def _csrf_tokens_match(self, request_csrf_token: Optional[str], cookie_csrf_token: Optional[str]) -> bool:
        """Take the CSRF tokens from the request and the cookie and verify both are valid and identical."""
        if not (request_csrf_token and cookie_csrf_token):
            return False

        decoded_request_token = self._decode_csrf_token(request_csrf_token)
        decoded_cookie_token = self._decode_csrf_token(cookie_csrf_token)
        if decoded_request_token is None or decoded_cookie_token is None:
            return False

        return secrets.compare_digest(decoded_request_token, decoded_cookie_token)
