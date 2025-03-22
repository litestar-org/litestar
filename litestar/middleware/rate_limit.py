from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from litestar.datastructures import MutableScopeHeaders
from litestar.exceptions import TooManyRequestsException
from litestar.middleware import ASGIMiddleware
from litestar.serialization import decode_json, encode_json
from litestar.utils import ensure_async_callable

__all__ = ("CacheObject", "RateLimitConfig", "RateLimitMiddleware")


if TYPE_CHECKING:
    from collections.abc import Awaitable

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


class RateLimitMiddleware(ASGIMiddleware):
    """Rate-limiting middleware."""

    def __init__(self, config: RateLimitConfig) -> None:
        """Initialize ``RateLimitMiddleware``.

        Args:
            config: An instance of RateLimitConfig.
        """
        self.check_throttle_handler = cast("Callable[[Request], Awaitable[bool]] | None", config.check_throttle_handler)
        self.config = config
        self.max_requests: int = config.rate_limit[1]
        self.unit: DurationUnit = config.rate_limit[0]

        self.exclude_opt_key = config.exclude_opt_key
        self.exclude_path_pattern = config.exclude

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        app = scope["litestar_app"]
        request: Request[Any, Any, Any] = app.request_class(scope)
        store = self.config.get_store_from_app(app)
        if await self.should_check_request(request=request):
            key = self.cache_key_from_request(request=request)
            cache_object = await self.retrieve_cached_history(key, store)
            if len(cache_object.history) >= self.max_requests:
                raise TooManyRequestsException(
                    headers=self.create_response_headers(cache_object=cache_object)
                    if self.config.set_rate_limit_headers
                    else None
                )
            await self.set_cached_history(key=key, cache_object=cache_object, store=store)
            if self.config.set_rate_limit_headers:
                send = self.create_send_wrapper(send=send, cache_object=cache_object)

        await next_app(scope, receive, send)  # pyright: ignore

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

        return f"{type(self).__name__}::{identifier}"

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
            self.config.rate_limit_policy_header_key: f"{self.max_requests}; w={DURATION_VALUES[self.unit]}",
            self.config.rate_limit_limit_header_key: str(self.max_requests),
            self.config.rate_limit_remaining_header_key: remaining_requests,
            self.config.rate_limit_reset_header_key: str(cache_object.reset - int(time())),
        }


@dataclass
class RateLimitConfig:
    """Configuration for ``RateLimitMiddleware``"""

    rate_limit: tuple[DurationUnit, int]
    """A tuple containing a time unit (second, minute, hour, day) and quantity, e.g. ("day", 1) or ("minute", 5)."""
    exclude: str | tuple[str, ...] | None = field(default=None)
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
            self.check_throttle_handler = ensure_async_callable(self.check_throttle_handler)  # type: ignore[arg-type]

    def get_store_from_app(self, app: Litestar) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Litestar <.app.Litestar>` instance."""
        return app.stores.get(self.store)
