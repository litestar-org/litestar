from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING, Any, Literal, cast

from litestar.datastructures import MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.exceptions import TooManyRequestsException
from litestar.middleware.base import AbstractMiddleware, DefineMiddleware
from litestar.serialization import decode_json, encode_json
from litestar.utils import ensure_async_callable

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


class RateLimitMiddleware(AbstractMiddleware):
    """Rate-limiting middleware."""

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
        self.rate_limits: list[tuple[DurationUnit, int]] = config._all_rate_limits
        self.get_identifier_for_request = config.identifier_for_request

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        app = scope["litestar_app"]
        request: Request[Any, Any, Any] = app.request_class(scope)
        store = self.config.get_store_from_app(app)
        if await self.should_check_request(request=request):
            identifier = self.get_identifier_for_request(request)
            key = f"{type(self).__name__}::{identifier}"
            route_handler = request.scope["route_handler"]
            if getattr(route_handler, "is_mount", False):
                key += "::mount"

            # Check every rate limit condition before updating any cache entry so that a
            # request that violates a later condition does not consume quota from earlier ones.
            checked: list[tuple[DurationUnit, int, CacheObject, str]] = []
            for unit, max_requests in self.rate_limits:
                limit_key = f"{key}::{unit}"
                cache_object = await self.retrieve_cached_history(limit_key, unit, store)
                if len(cache_object.history) >= max_requests:
                    raise TooManyRequestsException(
                        headers=self.create_response_headers(
                            cache_object=cache_object,
                            max_requests=max_requests,
                            unit=unit,
                        )
                        if self.config.set_rate_limit_headers
                        else None
                    )
                checked.append((unit, max_requests, cache_object, limit_key))

            # All limits passed — persist updated histories
            for unit, max_requests, cache_object, limit_key in checked:
                await self.set_cached_history(key=limit_key, cache_object=cache_object, unit=unit, store=store)

            if self.config.set_rate_limit_headers:
                # Use the most restrictive limit (fewest remaining requests) for response headers
                most_restrictive = min(checked, key=lambda x: x[1] - len(x[2].history))
                r_unit, r_max, r_cache, _ = most_restrictive
                send = self.create_send_wrapper(send=send, cache_object=r_cache, max_requests=r_max, unit=r_unit)

        await self.app(scope, receive, send)  # pyright: ignore

    def create_send_wrapper(
        self,
        send: Send,
        cache_object: CacheObject,
        max_requests: int | None = None,
        unit: DurationUnit | None = None,
    ) -> Send:
        """Create a ``send`` function that wraps the original send to inject response headers.

        Args:
            send: The ASGI send function.
            cache_object: A StorageObject instance.
            max_requests: Maximum number of requests for the selected rate limit window.
                Defaults to the first configured rate limit's max.
            unit: The duration unit for the selected rate limit window.
                Defaults to the first configured rate limit's unit.

        Returns:
            Send wrapper callable.
        """
        if max_requests is None:
            max_requests = self.rate_limits[0][1]
        if unit is None:
            unit = self.rate_limits[0][0]

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
                    cache_object=cache_object, max_requests=max_requests, unit=unit
                ).items():
                    headers[key] = value
            await send(message)

        return send_wrapper

    async def retrieve_cached_history(self, key: str, unit: DurationUnit, store: Store) -> CacheObject:
        """Retrieve a list of time stamps for the given duration unit.

        Args:
            key: Cache key.
            unit: The :data:`DurationUnit` for this rate limit window.
            store: A :class:`Store <.stores.base.Store>`

        Returns:
            An :class:`CacheObject`.
        """
        duration = DURATION_VALUES[unit]
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

    async def set_cached_history(self, key: str, cache_object: CacheObject, unit: DurationUnit, store: Store) -> None:
        """Store history extended with the current timestamp in cache.

        Args:
            key: Cache key.
            cache_object: A :class:`CacheObject`.
            unit: The :data:`DurationUnit` for this rate limit window.
            store: A :class:`Store <.stores.base.Store>`

        Returns:
            None
        """
        cache_object.history = [int(time()), *cache_object.history]
        await store.set(key, encode_json(cache_object), expires_in=DURATION_VALUES[unit])

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
        self,
        cache_object: CacheObject,
        max_requests: int | None = None,
        unit: DurationUnit | None = None,
    ) -> dict[str, str]:
        """Create ratelimit response headers.

        Notes:
            * see the `IETF RateLimit draft <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/>`_

        Args:
            cache_object: A :class:`CacheObject`.
            max_requests: Maximum number of requests for the chosen rate limit window.
                Defaults to the first configured rate limit's max.
            unit: The :data:`DurationUnit` for the chosen rate limit window.
                Defaults to the first configured rate limit's unit.

        Returns:
            A dict of http headers.
        """
        if max_requests is None:
            max_requests = self.rate_limits[0][1]
        if unit is None:
            unit = self.rate_limits[0][0]

        remaining_requests = str(
            max_requests - len(cache_object.history) if len(cache_object.history) <= max_requests else 0
        )

        return {
            self.config.rate_limit_policy_header_key: f"{max_requests}; w={DURATION_VALUES[unit]}",
            self.config.rate_limit_limit_header_key: str(max_requests),
            self.config.rate_limit_remaining_header_key: remaining_requests,
            self.config.rate_limit_reset_header_key: str(cache_object.reset - int(time())),
        }


@dataclass
class RateLimitConfig:
    """Configuration for ``RateLimitMiddleware``"""

    rate_limit: tuple[DurationUnit, int] | None = field(default=None)
    """A tuple containing a time unit (second, minute, hour, day) and quantity, e.g. ``("day", 1)`` or
    ``("minute", 5)``.

    Use :attr:`rate_limits` to specify multiple simultaneous rate limit conditions.  When both ``rate_limit``
    and ``rate_limits`` are ``None`` a :exc:`ValueError` is raised at initialisation time.
    """
    rate_limits: list[tuple[DurationUnit, int]] | None = field(default=None)
    """A list of ``(unit, max_requests)`` tuples that are ALL enforced simultaneously.

    A ``429 Too Many Requests`` response is returned as soon as *any* condition is breached.  This lets you
    combine multiple time windows, for example::

        RateLimitConfig(rate_limits=[("second", 10), ("minute", 100), ("hour", 2000)])

    When ``rate_limit`` is also provided a :exc:`ValueError` is raised.  When only ``rate_limit`` is
    provided it is normalised to a single-element list internally, so all existing code continues to work
    without modification.
    """
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
        if self.rate_limit is None and not self.rate_limits:
            raise ValueError("Either 'rate_limit' or 'rate_limits' must be provided to RateLimitConfig.")
        if self.rate_limit is not None and self.rate_limits is not None:
            raise ValueError(
                "Provide either 'rate_limit' or 'rate_limits' to RateLimitConfig, not both."
            )
        if self.check_throttle_handler:
            self.check_throttle_handler = ensure_async_callable(self.check_throttle_handler)  # type: ignore[arg-type]

    @property
    def _all_rate_limits(self) -> list[tuple[DurationUnit, int]]:
        """Return a normalised list of ``(unit, max_requests)`` tuples.

        Always use this property rather than accessing :attr:`rate_limit` or :attr:`rate_limits`
        directly so that the single-limit backward-compatible form is handled transparently.
        """
        if self.rate_limits is not None:
            return self.rate_limits
        assert self.rate_limit is not None  # guarded by __post_init__
        return [self.rate_limit]

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
                def my_handler(request: Request) -> None: ...


                app = Litestar(route_handlers=[my_handler], middleware=[throttle_config.middleware])

            Multiple simultaneous conditions are also supported:

            .. code-block::  python

                from litestar.middleware.rate_limit import RateLimitConfig

                # max 5/second AND max 100/minute AND max 1000/hour — all enforced at once
                throttle_config = RateLimitConfig(
                    rate_limits=[("second", 5), ("minute", 100), ("hour", 1000)]
                )

        Returns:
            An instance of :class:`DefineMiddleware <.middleware.base.DefineMiddleware>` including ``self`` as the
            config kwarg value.
        """
        return DefineMiddleware(self.middleware_class, config=self)

    def get_store_from_app(self, app: Litestar) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Litestar <.app.Litestar>` instance."""
        return app.stores.get(self.store)
