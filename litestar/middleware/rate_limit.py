from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from litestar.datastructures import MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.exceptions import TooManyRequestsException
from litestar.middleware.base import AbstractMiddleware, DefineMiddleware
from litestar.serialization import decode_json, encode_json
from litestar.utils import ensure_async_callable

__all__ = ("CacheObject", "RateLimitConfig", "RateLimitMiddleware")


if TYPE_CHECKING:
    from typing import Awaitable

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


class RateLimitMiddleware(AbstractMiddleware):
    """Rate-limiting middleware."""

    __slots__ = ("app", "check_throttle_handler", "max_requests", "unit", "request_quota", "config")

    def __init__(self, app: ASGIApp, config: RateLimitConfig) -> None:
        """Initialize ``RateLimitMiddleware``.

        Args:
            app: The ``next`` ASGI app to call.
            config: An instance of RateLimitConfig.
        """
        super().__init__(
            app=app, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key, scopes={ScopeType.HTTP}
        )
        self.check_throttle_handler = cast("Callable[[Request], Awaitable[bool]] | None", config.check_throttle_handler)
        self.config = config

        rate_limits = config.rate_limit if isinstance(config.rate_limit, list) else [config.rate_limit]
        if len(rate_limits) == 0:
            raise ValueError("rate_limit cannot be empty")

        self.limits: list[tuple[int, int]] = [(DURATION_VALUES[unit], n) for unit, n in rate_limits]
        self.limits.sort(key=lambda x: x[0])
        self.max_limit = self.limits[-1][0]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        app = scope["app"]
        request: Request[Any, Any, Any] = app.request_class(scope)
        store = self.config.get_store_from_app(app)
        now = int(time())
        if await self.should_check_request(request=request):
            key = self.cache_key_from_request(request=request)
            cache_object = await self.retrieve_cached_history(key, store)
            limit_usages = _count_requests(cache_object.history, self.limits, now)
            limit_most_restrictive, n = min(
                sorted(limit_usages.items(), key=lambda x: x[0][0], reverse=True), key=lambda x: x[0][1] - x[1]
            )

            if limit_most_restrictive[1] - n <= 0:
                raise TooManyRequestsException(
                    headers=self.create_response_headers(
                        cache_object=cache_object,
                        limit_most_restrictive=limit_most_restrictive,
                        requests_remaining=limit_most_restrictive[1] - n,
                    )
                    if self.config.set_rate_limit_headers
                    else None
                )

            await self.set_cached_history(key=key, cache_object=cache_object, store=store)
            if self.config.set_rate_limit_headers:
                send = self.create_send_wrapper(
                    send=send,
                    cache_object=cache_object,
                    limit_most_restrictive=limit_most_restrictive,
                    requests_remaining=limit_most_restrictive[1] - n - 1,
                )

        await self.app(scope, receive, send)  # pyright: ignore

    def create_send_wrapper(
        self, send: Send, cache_object: CacheObject, limit_most_restrictive: tuple[int, int], requests_remaining: int
    ) -> Send:
        """Create a ``send`` function that wraps the original send to inject response headers.

        Args:
            send: The ASGI send function.
            cache_object: A StorageObject instance.
            limit_most_restrictive: The most restrictive limit
            requests_remaining: The number of remaining requests
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
                for key, value in self.create_response_headers(
                    cache_object=cache_object,
                    limit_most_restrictive=limit_most_restrictive,
                    requests_remaining=requests_remaining,
                ).items():
                    headers.add(key, value)
            await send(message)

        return send_wrapper

    def cache_key_from_request(self, request: Request[Any, Any, Any]) -> str:
        """Get a cache-key from a ``Request``

        Args:
            request: A :class:`Request <.connection.Request>` instance.

        Returns:
            A cache key.
        """
        host = request.client.host if request.client else "anonymous"
        identifier = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP") or host
        route_handler = request.scope["route_handler"]
        if getattr(route_handler, "is_mount", False):
            identifier += "::mount"

        if getattr(route_handler, "is_static", False):
            identifier += "::static"

        return f"{type(self).__name__}::{identifier}"

    async def retrieve_cached_history(self, key: str, store: Store) -> CacheObject:
        """Retrieve a list of time stamps for the given duration unit.

        Args:
            key: Cache key.
            store: A :class:`Store <.stores.base.Store>`

        Returns:
            An :class:`CacheObject`.
        """
        duration = self.max_limit
        now = int(time())
        cached_string = await store.get(key)
        if cached_string:
            cache_object = CacheObject(**decode_json(value=cached_string))
            if cache_object.reset <= now:
                return CacheObject(history=[], reset=now + duration)

            while cache_object.history and cache_object.history[-1] <= now - duration:
                cache_object.history.pop()
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
        await store.set(key, encode_json(cache_object), expires_in=self.max_limit)

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

    def create_response_headers(
        self, cache_object: CacheObject, limit_most_restrictive: tuple[int, int], requests_remaining: int
    ) -> dict[str, str]:
        """Create ratelimit response headers.

        Notes:
            * see the `IETF RateLimit draft <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/>_`

        Args:
            cache_object:A :class:`CacheObject`.
            limit_most_restrictive: The most restrictive limit applicable to this request
            requests_remaining: The number of requests remaining before the limit is exceeded

        Returns:
            A dict of http headers.
        """

        rate_limit_policy = ", ".join([f"{o[1]};w={o[0]}" for o in self.limits])

        return {
            self.config.rate_limit_policy_header_key: rate_limit_policy,
            self.config.rate_limit_limit_header_key: str(limit_most_restrictive[1]),
            self.config.rate_limit_remaining_header_key: str(max(requests_remaining, 0)),
            self.config.rate_limit_reset_header_key: str(int(time()) - cache_object.reset),
        }


@dataclass
class RateLimitConfig:
    """Configuration for ``RateLimitMiddleware``"""

    rate_limit: tuple[DurationUnit, int] | list[tuple[DurationUnit, int]]
    """An option for configuring the rate limit containing either a time unit (second, minute, hour, day) and quantity, e.g. ("day", 1) or ("minute", 5) or a list of these tuples """
    exclude: str | list[str] | None = field(default=None)
    """A pattern or list of patterns to skip in the rate limiting middleware."""
    exclude_opt_key: str | None = field(default=None)
    """An identifier to use on routes to disable rate limiting for a particular route."""
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
            self.check_throttle_handler = ensure_async_callable(self.check_throttle_handler)  # type: ignore

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one of the application layers.

        Examples:
            .. code-block::  python

                from litestar import Litestar, Request, get
                from litestar.middleware.rate_limit import RateLimitConfig

                # limit to 10 requests per minute, excluding the schema path
                throttle_config = RateLimitConfig(rate_limit=("minute", 10), exclude=["/schema"])


                @get("/")
                def my_handler(request: Request) -> None:
                    ...


                app = Litestar(route_handlers=[my_handler], middleware=[throttle_config.middleware])

        Returns:
            An instance of :class:`DefineMiddleware <.middleware.base.DefineMiddleware>` including ``self`` as the
            config kwarg value.
        """
        return DefineMiddleware(self.middleware_class, config=self)

    def get_store_from_app(self, app: Litestar) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Litestar <.app.Litestar>` instance."""
        return app.stores.get(self.store)


def _count_requests(requests: list[int], limits: list[tuple[int, int]], time_now: int) -> dict[tuple[int, int], int]:
    """Counts the number of requests within each limit's window. Runs in O(n+m) time.

    Notes:
        Assumes that `requests` are sorted in descending order and the `limits` are sorted in descending order based on
        the size of the limit's time window.

    Args:
        requests: Timestamps representing the requests.
        limits: The limits.
        time_now: The current time used to calculate the limits' window ranges.

    Returns:
        A mapping from the limits to their usages.
    """
    count_by_limit: dict[tuple[int, int], int] = {w: 0 for w in limits}

    if not requests or not limits:
        return count_by_limit

    requests.append(requests[-1] - limits[-1][0])
    requests.insert(0, max(time_now, requests[0]) + 1)

    curr_limit_idx = 0
    left, right = 0, 1
    while right < len(requests):
        while curr_limit_idx < len(limits) and time_now - limits[curr_limit_idx][0] >= requests[right]:
            count_by_limit[limits[curr_limit_idx]] = left
            curr_limit_idx += 1
        left += 1
        right += 1

    requests.pop()
    requests.pop(0)
    return count_by_limit
