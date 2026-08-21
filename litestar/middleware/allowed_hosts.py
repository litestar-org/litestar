from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING

from litestar.datastructures import URL, MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware
from litestar.response.base import ASGIResponse
from litestar.response.redirect import ASGIRedirectResponse
from litestar.status_codes import HTTP_400_BAD_REQUEST

__all__ = ("AllowedHostsMiddleware",)


if TYPE_CHECKING:
    from litestar.config.allowed_hosts import AllowedHostsConfig
    from litestar.types import ASGIApp, Receive, Scope, Scopes, Send


class AllowedHostsMiddleware(ASGIMiddleware):
    """Middleware ensuring the host of a request originated in a trusted host."""

    def __init__(
        self,
        *,
        allowed_hosts: list[str] | None = None,
        exclude: str | list[str] | None = None,
        exclude_opt_key: str | None = None,
        scopes: Scopes | None = None,
        www_redirect: bool = True,
    ) -> None:
        """Initialize ``AllowedHostsMiddleware``.

        Args:
            allowed_hosts: A list of trusted hosts. Use ``*`` to allow all hosts, or prefix
                domains with ``*.`` to allow all subdomains. Wildcard placement is validated
                by :class:`~litestar.config.allowed_hosts.AllowedHostsConfig`, not here.
            exclude: A pattern or list of patterns to skip.
            exclude_opt_key: An identifier to use on routes to disable the host check for a
                particular route.
            scopes: ASGI scopes processed by the middleware; if ``None`` or empty, ``http``,
                ``websocket`` and ASGI route handlers are all processed. Mounted ASGI apps
                stay wrapped regardless, with their connections filtered by scope type.
            www_redirect: A boolean dictating whether to redirect requests that start with
                ``www.`` and otherwise match a trusted host.
        """
        self.exclude_path_pattern = tuple(exclude) if isinstance(exclude, list) else exclude
        self.exclude_opt_key = exclude_opt_key
        if scopes:
            scope_types = frozenset(scopes)
            self.scopes = (*(s for s in (ScopeType.HTTP, ScopeType.WEBSOCKET) if s in scope_types), ScopeType.ASGI)
            self.should_bypass_for_scope = lambda scope: scope["type"] not in scope_types

        self.allowed_hosts = ["*"] if allowed_hosts is None else list(allowed_hosts)
        self.www_redirect = www_redirect
        self.allowed_hosts_regex: Pattern | None = None
        self.redirect_domains: Pattern | None = None

        if any(host == "*" for host in self.allowed_hosts):
            return

        allowed_hosts_patterns: set[str] = {
            rf".*\.{re.escape(host.replace('*.', ''))}$" if host.startswith("*.") else re.escape(host)
            for host in self.allowed_hosts
        }

        self.allowed_hosts_regex = re.compile("|".join(sorted(allowed_hosts_patterns)))
        if www_redirect and (
            redirect_domains := {host.replace("www.", "") for host in self.allowed_hosts if host.startswith("www.")}
        ):
            self.redirect_domains = re.compile("|".join(sorted(redirect_domains)))

    @classmethod
    def from_config(cls, config: AllowedHostsConfig) -> AllowedHostsMiddleware:
        """Create an instance from an :class:`~litestar.config.allowed_hosts.AllowedHostsConfig`."""
        return cls(
            allowed_hosts=config.allowed_hosts,
            exclude=config.exclude,
            exclude_opt_key=config.exclude_opt_key,
            scopes=config.scopes,
            www_redirect=config.www_redirect,
        )

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
        if self.allowed_hosts_regex is None:
            await next_app(scope, receive, send)
            return

        headers = MutableScopeHeaders(scope=scope)
        if (host := headers.get("host")) is not None and host.split(":")[0]:
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
