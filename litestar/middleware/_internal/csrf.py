from __future__ import annotations

import hashlib
import hmac
import secrets
from secrets import compare_digest
from typing import TYPE_CHECKING, Any, Literal

from litestar.datastructures import MutableScopeHeaders
from litestar.datastructures.cookie import Cookie
from litestar.enums import RequestEncodingType, ScopeType
from litestar.exceptions import PermissionDeniedException
from litestar.middleware.base import ASGIMiddleware
from litestar.utils.scope.state import ScopeState

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar.connection import Request
    from litestar.types import (
        ASGIApp,
        HTTPSendMessage,
        Message,
        Method,
        Receive,
        Scope,
        Send,
    )

__all__ = ("CSRFMiddleware",)

CSRF_SECRET_BYTES = 32
CSRF_SECRET_LENGTH = CSRF_SECRET_BYTES * 2


def generate_csrf_hash(token: str, secret: str) -> str:
    """Generate an HMAC that signs the CSRF token.

    Args:
        token: A hashed token.
        secret: A secret value.

    Returns:
        A CSRF hash.
    """
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def generate_csrf_token(secret: str) -> str:
    """Generate a CSRF token that includes a randomly generated string signed by an HMAC.

    Args:
        secret: A secret string.

    Returns:
        A unique CSRF token.
    """
    token = secrets.token_hex(CSRF_SECRET_BYTES)
    token_hash = generate_csrf_hash(token=token, secret=secret)
    return token + token_hash


class CSRFMiddleware(ASGIMiddleware):
    """CSRF Middleware class.

    This Middleware protects against attacks by setting a CSRF cookie with a token and verifying it in request headers.
    """

    scopes = (ScopeType.HTTP, ScopeType.ASGI)

    def __init__(
        self,
        secret: str,
        *,
        cookie_name: str = "csrftoken",
        cookie_path: str = "/",
        header_name: str = "x-csrftoken",
        cookie_secure: bool = False,
        cookie_httponly: bool = False,
        cookie_samesite: Literal["lax", "strict", "none"] = "lax",
        cookie_domain: str | None = None,
        safe_methods: Iterable[Method] = ("GET", "HEAD", "OPTIONS"),
        exclude: str | list[str] | None = None,
        exclude_opt_key: str = "exclude_from_csrf",
    ) -> None:
        """Initialize ``CSRFMiddleware``.

        Args:
            secret: A string that is used to create an HMAC to sign the CSRF token.
            cookie_name: The CSRF cookie name.
            cookie_path: The CSRF cookie path.
            header_name: The header that will be expected in each request.
            cookie_secure: A boolean value indicating whether to set the ``Secure`` attribute on the cookie.
            cookie_httponly: A boolean value indicating whether to set the ``HttpOnly`` attribute on the cookie.
            cookie_samesite: The value to set in the ``SameSite`` attribute of the cookie.
            cookie_domain: Specifies which hosts can receive the cookie.
            safe_methods: A set of "safe methods" that can set the cookie.
            exclude: A pattern or list of patterns to skip in the CSRF middleware, matched against the handler path.
            exclude_opt_key: An identifier to use on routes to disable CSRF for a particular route.
        """
        self.secret = secret
        self.cookie_name = cookie_name
        self.cookie_path = cookie_path
        self.header_name = header_name
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite: Literal["lax", "strict", "none"] = cookie_samesite
        self.cookie_domain = cookie_domain
        self.safe_methods = set(safe_methods)
        self.exclude_path_pattern = tuple(exclude) if isinstance(exclude, list) else exclude
        self.exclude_opt_key = exclude_opt_key

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Handle ASGI call.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
            next_app: The next ASGI application in the middleware stack to call.

        Returns:
            None
        """
        if scope["type"] != ScopeType.HTTP:
            await next_app(scope, receive, send)
            return

        request: Request[Any, Any, Any] = scope["litestar_app"].request_class(scope=scope, receive=receive)
        content_type, _ = request.content_type
        csrf_cookie = request.cookies.get(self.cookie_name)
        existing_csrf_token = request.headers.get(self.header_name)

        if not existing_csrf_token and content_type in {
            RequestEncodingType.URL_ENCODED,
            RequestEncodingType.MULTI_PART,
        }:
            form = await request.form()
            existing_csrf_token = form.get("_csrf_token", None)

        connection_state = ScopeState.from_scope(scope)
        if request.method in self.safe_methods:
            token = connection_state.csrf_token = csrf_cookie or generate_csrf_token(secret=self.secret)
            await next_app(scope, receive, self.create_send_wrapper(send=send, csrf_cookie=csrf_cookie, token=token))
        elif (
            existing_csrf_token is not None
            and csrf_cookie is not None
            and self._csrf_tokens_match(existing_csrf_token, csrf_cookie)
        ):
            connection_state.csrf_token = existing_csrf_token
            await next_app(scope, receive, send)
        else:
            raise PermissionDeniedException("CSRF token verification failed")

    def create_send_wrapper(self, send: Send, token: str, csrf_cookie: str | None) -> Send:
        """Wrap ``send`` to handle CSRF validation.

        Args:
            token: The CSRF token.
            send: The ASGI send function.
            csrf_cookie: CSRF cookie.

        Returns:
            An ASGI send function.
        """

        async def send_wrapper(message: Message) -> None:
            """Send function that wraps the original send to inject a cookie.

            Args:
                message: An ASGI ``Message``

            Returns:
                None
            """
            if csrf_cookie is None and message["type"] == "http.response.start":
                message.setdefault("headers", [])
                self._set_cookie_if_needed(message=message, token=token)
            await send(message)

        return send_wrapper

    def _set_cookie_if_needed(self, message: HTTPSendMessage, token: str) -> None:
        headers = MutableScopeHeaders.from_message(message)
        cookie = Cookie(
            key=self.cookie_name,
            value=token,
            path=self.cookie_path,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
            domain=self.cookie_domain,
        )
        headers.add("set-cookie", cookie.to_header(header=""))

    def _decode_csrf_token(self, token: str) -> str | None:
        """Decode a CSRF token and validate its HMAC."""
        if len(token) < CSRF_SECRET_LENGTH + 1:
            return None

        token_secret = token[:CSRF_SECRET_LENGTH]
        existing_hash = token[CSRF_SECRET_LENGTH:]
        expected_hash = generate_csrf_hash(token=token_secret, secret=self.secret)
        return token_secret if compare_digest(existing_hash, expected_hash) else None

    def _csrf_tokens_match(self, request_csrf_token: str, cookie_csrf_token: str) -> bool:
        """Take the CSRF tokens from the request and the cookie and verify both are valid and identical."""
        decoded_request_token = self._decode_csrf_token(request_csrf_token)
        decoded_cookie_token = self._decode_csrf_token(cookie_csrf_token)
        if decoded_request_token is None or decoded_cookie_token is None:
            return False

        return compare_digest(decoded_request_token, decoded_cookie_token)
