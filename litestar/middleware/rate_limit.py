from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING, Any, Literal, cast

import anyio

from litestar.datastructures import MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.exceptions import TooManyRequestsException
from litestar.middleware.base import ASGIMiddleware
from litestar.serialization import decode_json, encode_json
from litestar.utils import ensure_async_callable
from litestar.utils.deprecation import warn_deprecation

__all__ = (
    "CacheObject",
    "RateLimitConfig",
    "RateLimitMiddleware",
    "get_remote_address",
)


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from litestar import Litestar
    from litestar.connection import Request
    from litestar.stores.base import Store
    from litestar.types import ASGIApp, Message, Receive, Scope, Send, SyncOrAsyncUnion


DurationUnit = Literal["second", "minute", "hour", "day"]

DURATION_VALUES: dict[DurationUnit, int] = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


@dataclass
class CacheObject:
    """Representation of a cached object's metadata."""

    __slots__ = ("history", "reset")

    history: list[int]
    reset: int


def get_remote_address(request: Request[Any, Any, Any]) -> str:
    """Get a client's remote address from a ``Request``

    Args:
        request: A :class:`Request <.connection.Request>` instance.

    Returns:
        An address, uniquely identifying this client
    """
    return request.client.host if request.client else "127.0.0.1"


class RateLimitMiddleware(ASGIMiddleware):
    """Rate-limiting middleware."""

    scopes = (ScopeType.HTTP, ScopeType.ASGI)

    def __init__(
        self,
        rate_limit: tuple[DurationUnit, int],
        *,
        store: str = "rate_limit",
        identifier_for_request: Callable[[Request[Any, Any, Any]], str] = get_remote_address,
        check_throttle_handler: Callable[[Request[Any, Any, Any]], SyncOrAsyncUnion[bool]] | None = None,
        set_rate_limit_headers: bool = True,
        rate_limit_policy_header_key: str = "RateLimit-Policy",
        rate_limit_limit_header_key: str = "RateLimit-Limit",
        rate_limit_remaining_header_key: str = "RateLimit-Remaining",
        rate_limit_reset_header_key: str = "RateLimit-Reset",
        exclude: str | list[str] | None = None,
        exclude_opt_key: str | None = None,
    ) -> None:
        """Initialize ``RateLimitMiddleware``.

        Args:
            rate_limit: A tuple containing a time unit (second, minute, hour, day) and quantity, e.g. ("day", 1) or
                ("minute", 5).
            store: Name of the :class:`Store <.stores.base.Store>` to use, looked up on the application's store
                registry.
            identifier_for_request: A callable that receives the request and returns an identifier for which the
                limit should be applied.
            check_throttle_handler: Handler callable that receives the request instance, returning a boolean dictating
                whether or not the request should be checked for rate limiting.
            set_rate_limit_headers: Boolean dictating whether to set the rate limit headers on the response.
            rate_limit_policy_header_key: Key to use for the rate limit policy header.
            rate_limit_limit_header_key: Key to use for the rate limit limit header.
            rate_limit_remaining_header_key: Key to use for the rate limit remaining header.
            rate_limit_reset_header_key: Key to use for the rate limit reset header.
            exclude: A pattern or list of patterns to skip in the rate limiting middleware, matched against the
                handler path.
            exclude_opt_key: An identifier to use on routes to disable rate limiting for a particular route.
        """
        self.unit: DurationUnit = rate_limit[0]
        self.max_requests: int = rate_limit[1]
        self.store = store
        self.get_identifier_for_request = identifier_for_request
        self.check_throttle_handler = cast(
            "Callable[[Request], Awaitable[bool]] | None",
            ensure_async_callable(check_throttle_handler) if check_throttle_handler else None,
        )
        self.set_rate_limit_headers = set_rate_limit_headers
        self.rate_limit_policy_header_key = rate_limit_policy_header_key
        self.rate_limit_limit_header_key = rate_limit_limit_header_key
        self.rate_limit_remaining_header_key = rate_limit_remaining_header_key
        self.rate_limit_reset_header_key = rate_limit_reset_header_key
        self.exclude_path_pattern = tuple(exclude) if isinstance(exclude, list) else exclude
        self.exclude_opt_key = exclude_opt_key
        self._lock = anyio.Lock()

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

        app = scope["litestar_app"]
        request: Request[Any, Any, Any] = app.request_class(scope)
        store = app.stores.get(self.store)
        if await self.should_check_request(request=request):
            identifier = self.get_identifier_for_request(request)
            key = f"{type(self).__name__}::{identifier}"
            route_handler = request.scope["route_handler"]
            if getattr(route_handler, "is_mount", False):
                key += "::mount"

            async with self._lock:
                cache_object = await self.retrieve_cached_history(key, store)
                if len(cache_object.history) >= self.max_requests:
                    raise TooManyRequestsException(
                        headers=self.create_response_headers(cache_object=cache_object)
                        if self.set_rate_limit_headers
                        else None
                    )
                await self.set_cached_history(key=key, cache_object=cache_object, store=store)
            if self.set_rate_limit_headers:
                send = self.create_send_wrapper(send=send, cache_object=cache_object)

        await next_app(scope, receive, send)

    def create_send_wrapper(self, send: Send, cache_object: CacheObject) -> Send:
        """Create a ``send`` function that wraps the original send to inject response headers.

        Args:
            send: The ASGI send function.
            cache_object: A StorageObject instance.

        Returns:
            Send wrapper callable.
        """

        async def send_wrapper(message: Message) -> None:
            """Wrap the ASGI ``Send`` callable.

            Args:
                message: An ASGI ``Message``

            Returns:
                None
            """
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                headers = MutableScopeHeaders(message)
                for key, value in self.create_response_headers(cache_object=cache_object).items():
                    headers[key] = value
            await send(message)

        return send_wrapper

    async def retrieve_cached_history(self, key: str, store: Store) -> CacheObject:
        """Retrieve a list of time stamps for the given duration unit.

        Args:
            key: Cache key.
            store: A :class:`Store <.stores.base.Store>`

        Returns:
            An :class:`CacheObject`.
        """
        duration = DURATION_VALUES[self.unit]
        now = int(time())
        cached_string = await store.get(key)
        if cached_string:
            cache_object = CacheObject(**decode_json(value=cached_string))
            if cache_object.reset <= now:
                return CacheObject(history=[], reset=now + duration)
            return cache_object

        return CacheObject(history=[], reset=now + duration)

    async def set_cached_history(self, key: str, cache_object: CacheObject, store: Store) -> None:
        """Store history extended with the current timestamp in cache.

        Args:
            key: Cache key.
            cache_object: A :class:`CacheObject`.
            store: A :class:`Store <.stores.base.Store>`

        Returns:
            None
        """
        cache_object.history = [int(time()), *cache_object.history]
        await store.set(key, encode_json(cache_object), expires_in=DURATION_VALUES[self.unit])

    async def should_check_request(self, request: Request[Any, Any, Any]) -> bool:
        """Return a boolean indicating if a request should be checked for rate limiting.

        Args:
            request: A :class:`Request <.connection.Request>` instance.

        Returns:
            Boolean dictating whether the request should be checked for rate-limiting.
        """
        if self.check_throttle_handler:
            return await self.check_throttle_handler(request)
        return True

    def create_response_headers(self, cache_object: CacheObject) -> dict[str, str]:
        """Create ratelimit response headers.

        Notes:
            * see the `IETF RateLimit draft <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/>`_

        Args:
            cache_object:A :class:`CacheObject`.

        Returns:
            A dict of http headers.
        """
        remaining_requests = str(
            self.max_requests - len(cache_object.history) if len(cache_object.history) <= self.max_requests else 0
        )

        return {
            self.rate_limit_policy_header_key: f"{self.max_requests}; w={DURATION_VALUES[self.unit]}",
            self.rate_limit_limit_header_key: str(self.max_requests),
            self.rate_limit_remaining_header_key: remaining_requests,
            self.rate_limit_reset_header_key: str(cache_object.reset - int(time())),
        }


@dataclass
class RateLimitConfig:
    """Configuration for ``RateLimitMiddleware``"""

    rate_limit: tuple[DurationUnit, int]
    """A tuple containing a time unit (second, minute, hour, day) and quantity, e.g. ("day", 1) or ("minute", 5)."""
    exclude: str | list[str] | None = field(default=None)
    """A pattern or list of patterns to skip in the rate limiting middleware."""
    exclude_opt_key: str | None = field(default=None)
    """An identifier to use on routes to disable rate limiting for a particular route."""
    identifier_for_request: Callable[[Request], str] = get_remote_address
    """
    A callable that receives the request and returns an identifier for which the limit
    should be applied. Defaults to :func:`~litestar.middleware.rate_limit.get_remote_address`, which returns the client's
    address.

    Note that :func:`~litestar.middleware.rate_limit.get_remote_address` does *NOT* honour ``X-FORWARDED-FOR`` headers, as these cannot be
    trusted implicitly. If running behind a proxy, a secure way of updating the client's
    address should be implemented, such as uvicorn's
    `ProxyHeaderMiddleware <https://github.com/encode/uvicorn/blob/master/uvicorn/middleware/proxy_headers.py>`_
    or hypercon's `ProxyFixMiddleware <https://hypercorn.readthedocs.io/en/latest/how_to_guides/proxy_fix.html>`_ .
    """
    check_throttle_handler: Callable[[Request[Any, Any, Any]], SyncOrAsyncUnion[bool]] | None = field(default=None)
    """Handler callable that receives the request instance, returning a boolean dictating whether or not the request
    should be checked for rate limiting.
    """
    middleware_class: type[RateLimitMiddleware] = field(default=RateLimitMiddleware)
    """The middleware class to use."""
    set_rate_limit_headers: bool = field(default=True)
    """Boolean dictating whether to set the rate limit headers on the response."""
    rate_limit_policy_header_key: str = field(default="RateLimit-Policy")
    """Key to use for the rate limit policy header."""
    rate_limit_remaining_header_key: str = field(default="RateLimit-Remaining")
    """Key to use for the rate limit remaining header."""
    rate_limit_reset_header_key: str = field(default="RateLimit-Reset")
    """Key to use for the rate limit reset header."""
    rate_limit_limit_header_key: str = field(default="RateLimit-Limit")
    """Key to use for the rate limit limit header."""
    store: str = "rate_limit"
    """Name of the :class:`Store <.stores.base.Store>` to use"""

    def __post_init__(self) -> None:
        if self.check_throttle_handler:
            self.check_throttle_handler = ensure_async_callable(self.check_throttle_handler)  # type: ignore[arg-type]

    @property
    def middleware(self) -> RateLimitMiddleware:
        """Create an instance of :attr:`middleware_class`, configured from this config instance.

        .. deprecated:: 3.0
            Construct a :class:`RateLimitMiddleware` instance directly and pass it to the
            middleware list instead, e.g.
            ``middleware=[RateLimitMiddleware(rate_limit=("minute", 10), exclude=["/schema"])]``.

        Returns:
            An instance of :attr:`middleware_class`, configured from this config instance.
        """
        warn_deprecation(
            version="3.0",
            deprecated_name="RateLimitConfig.middleware",
            kind="property",
            removal_in="4.0",
            alternative="RateLimitMiddleware",
            info="Construct a RateLimitMiddleware instance directly and pass it to the middleware list",
        )
        return self.middleware_class(
            rate_limit=self.rate_limit,
            store=self.store,
            identifier_for_request=self.identifier_for_request,
            check_throttle_handler=self.check_throttle_handler,
            set_rate_limit_headers=self.set_rate_limit_headers,
            rate_limit_policy_header_key=self.rate_limit_policy_header_key,
            rate_limit_limit_header_key=self.rate_limit_limit_header_key,
            rate_limit_remaining_header_key=self.rate_limit_remaining_header_key,
            rate_limit_reset_header_key=self.rate_limit_reset_header_key,
            exclude=self.exclude,
            exclude_opt_key=self.exclude_opt_key,
        )

    def get_store_from_app(self, app: Litestar) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Litestar <.app.Litestar>` instance."""
        return app.stores.get(self.store)
