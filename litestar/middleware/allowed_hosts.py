from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING

from litestar.datastructures import URL, MutableScopeHeaders
from litestar.middleware import ASGIMiddleware
from litestar.response.base import ASGIResponse
from litestar.response.redirect import ASGIRedirectResponse
from litestar.status_codes import HTTP_400_BAD_REQUEST

__all__ = ("AllowedHostsMiddleware",)


if TYPE_CHECKING:
    from litestar.config.allowed_hosts import AllowedHostsConfig
    from litestar.types import ASGIApp, Receive, Scope, Send


class AllowedHostsMiddleware(ASGIMiddleware):
    """Middleware ensuring the host of a request originated in a trusted host."""

    def __init__(self, config: AllowedHostsConfig) -> None:
        """Initialize ``AllowedHostsMiddleware``.

        Args:
            config: An instance of AllowedHostsConfig.
        """

        self.allowed_hosts_regex: Pattern | None = None
        self.redirect_domains: Pattern | None = None

        if any(host == "*" for host in config.allowed_hosts):
            return

        allowed_hosts: set[str] = {
            rf".*\.{host.replace('*.', '')}$" if host.startswith("*.") else host for host in config.allowed_hosts
        }

        self.allowed_hosts_regex = re.compile("|".join(sorted(allowed_hosts)))  # pyright: ignore

        if config.www_redirect and (
            redirect_domains := {host.replace("www.", "") for host in config.allowed_hosts if host.startswith("www.")}
        ):
            self.redirect_domains = re.compile("|".join(sorted(redirect_domains)))  # pyright: ignore

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        if self.allowed_hosts_regex is None:
            await next_app(scope, receive, send)
            return

        headers = MutableScopeHeaders(scope=scope)
        if host := headers.get("host", headers.get("x-forwarded-host", "")).split(":")[0]:
            if self.allowed_hosts_regex.fullmatch(host):
                await next_app(scope, receive, send)
                return

            if self.redirect_domains is not None and self.redirect_domains.fullmatch(host):
                url = URL.from_scope(scope)
                redirect_url = url.with_replacements(netloc=f"www.{url.netloc}")
                redirect_response = ASGIRedirectResponse(path=str(redirect_url))
                await redirect_response(scope, receive, send)
                return

        response = ASGIResponse(body=b'{"message":"invalid host header"}', status_code=HTTP_400_BAD_REQUEST)
        await response(scope, receive, send)
