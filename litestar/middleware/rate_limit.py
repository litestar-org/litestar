from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING, Any, Literal, cast

import anyio

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
    from collections.abc import Awaitable, Callable, Sequence
    from typing import TypeGuard

    from litestar import Litestar
    from litestar.connection import Request
    from litestar.stores.base import Store
    from litestar.types import ASGIApp, Message, Receive, Scope, Send, SyncOrAsyncUnion


DurationUnit = Literal["second", "minute", "hour", "day"]

DURATION_VALUES: dict[DurationUnit, int] = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def _is_rate_limit(value: object) -> TypeGuard[tuple[DurationUnit, int]]:
    return isinstance(value, tuple) and len(value) == 2 and value[0] in DURATION_VALUES and isinstance(value[1], int)


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
        self._rate_limits = config._rate_limits
        self.unit: DurationUnit
        self.max_requests: int
        self.unit, self.max_requests = self._rate_limits[0]
        self.get_identifier_for_request = config.identifier_for_request
        self._lock = anyio.Lock()

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
            is_mount = getattr(route_handler, "is_mount", False)
            is_multi_window = len(self._rate_limits) > 1

            async with self._lock:
                cache_objects: list[tuple[DurationUnit, int, CacheObject]] = []
                for unit, max_requests in self._rate_limits:
                    cache_key = self._create_cache_key(key=key, unit=unit, is_mount=is_mount)
                    cache_object = (
                        await self._retrieve_cached_history(key=cache_key, store=store, unit=unit)
                        if is_multi_window
                        else await self.retrieve_cached_history(key=cache_key, store=store)
                    )
                    cache_objects.append((unit, max_requests, cache_object))

                for unit, max_requests, cache_object in cache_objects:
                    if len(cache_object.history) >= max_requests:
                        headers = None
                        if self.config.set_rate_limit_headers:
                            headers = (
                                self._create_response_headers(
                                    cache_object=cache_object, unit=unit, max_requests=max_requests
                                )
                                if is_multi_window
                                else self.create_response_headers(cache_object=cache_object)
                            )
                        raise TooManyRequestsException(headers=headers)
                for unit, _, cache_object in cache_objects:
                    cache_key = self._create_cache_key(key=key, unit=unit, is_mount=is_mount)
                    if is_multi_window:
                        await self._set_cached_history(key=cache_key, cache_object=cache_object, store=store, unit=unit)
                    else:
                        await self.set_cached_history(key=cache_key, cache_object=cache_object, store=store)
            if self.config.set_rate_limit_headers:
                unit, max_requests, cache_object = min(
                    cache_objects, key=lambda item: (item[1] - len(item[2].history), item[2].reset)
                )
                send = (
                    self._create_send_wrapper(
                        send=send, cache_object=cache_object, unit=unit, max_requests=max_requests
                    )
                    if is_multi_window
                    else self.create_send_wrapper(send=send, cache_object=cache_object)
                )

        await self.app(scope, receive, send)

    def _create_cache_key(self, key: str, unit: DurationUnit, is_mount: bool) -> str:
        """Create a cache key for a rate-limit window."""
        if len(self._rate_limits) > 1:
            key = f"{key}::{unit}"
        if is_mount:
            key += "::mount"
        return key

    def create_send_wrapper(self, send: Send, cache_object: CacheObject) -> Send:
        """Create a ``send`` function that wraps the original send to inject response headers.

        Args:
            send: The ASGI send function.
            cache_object: A StorageObject instance.

        Returns:
            Send wrapper callable.
        """
        return self._create_send_wrapper(send=send, cache_object=cache_object)

    def _create_send_wrapper(
        self,
        send: Send,
        cache_object: CacheObject,
        unit: DurationUnit | None = None,
        max_requests: int | None = None,
    ) -> Send:
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
                response_headers = (
                    self._create_response_headers(cache_object=cache_object, unit=unit, max_requests=max_requests)
                    if unit is not None and max_requests is not None
                    else self.create_response_headers(cache_object=cache_object)
                )
                for key, value in response_headers.items():
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
        return await self._retrieve_cached_history(key=key, store=store, unit=self.unit)

    async def _retrieve_cached_history(self, key: str, store: Store, unit: DurationUnit) -> CacheObject:
        duration = DURATION_VALUES[unit]
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
        await self._set_cached_history(key=key, cache_object=cache_object, store=store, unit=self.unit)

    async def _set_cached_history(self, key: str, cache_object: CacheObject, store: Store, unit: DurationUnit) -> None:
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

    def create_response_headers(self, cache_object: CacheObject) -> dict[str, str]:
        """Create ratelimit response headers.

        Notes:
            * see the `IETF RateLimit draft <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/>`_

        Args:
            cache_object:A :class:`CacheObject`.

        Returns:
            A dict of http headers.
        """
        return self._create_response_headers(cache_object=cache_object, unit=self.unit, max_requests=self.max_requests)

    def _create_response_headers(
        self, cache_object: CacheObject, unit: DurationUnit, max_requests: int
    ) -> dict[str, str]:
        remaining_requests = str(max(max_requests - len(cache_object.history), 0))
        policy = ", ".join(f"{limit}; w={DURATION_VALUES[rate_unit]}" for rate_unit, limit in self._rate_limits)

        return {
            self.config.rate_limit_policy_header_key: policy,
            self.config.rate_limit_limit_header_key: str(max_requests),
            self.config.rate_limit_remaining_header_key: remaining_requests,
            self.config.rate_limit_reset_header_key: str(cache_object.reset - int(time())),
        }


@dataclass
class RateLimitConfig:
    """Configuration for ``RateLimitMiddleware``"""

    rate_limit: tuple[DurationUnit, int] | Sequence[tuple[DurationUnit, int]]
    """One or more rate limits, e.g. ("minute", 5) or [("second", 1), ("minute", 5)]."""
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
    _rate_limits: tuple[tuple[DurationUnit, int], ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        rate_limits: tuple[tuple[DurationUnit, int], ...]
        if _is_rate_limit(self.rate_limit):
            rate_limits = (self.rate_limit,)
        else:
            rate_limits = tuple(cast("Sequence[tuple[DurationUnit, int]]", self.rate_limit))
        if not rate_limits:
            raise ValueError("rate_limit must contain at least one rate limit")
        self._rate_limits = rate_limits
        if self.check_throttle_handler:
            self.check_throttle_handler = ensure_async_callable(self.check_throttle_handler)  # type: ignore[arg-type]

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one of the application layers.

        Examples:
            .. code-block::  python

                from litestar import Litestar, Request, get
                from litestar.middleware.rate_limit import RateLimitConfig

                # reject a client when either window is exhausted
                throttle_config = RateLimitConfig(
                    rate_limit=[("second", 2), ("minute", 10)],
                    exclude=["/schema"],
                )


                @get("/")
                def my_handler(request: Request) -> None: ...


                app = Litestar(route_handlers=[my_handler], middleware=[throttle_config.middleware])

        Returns:
            An instance of :class:`DefineMiddleware <.middleware.base.DefineMiddleware>` including ``self`` as the
            config kwarg value.
        """
        return DefineMiddleware(self.middleware_class, config=self)

    def get_store_from_app(self, app: Litestar) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Litestar <.app.Litestar>` instance."""
        return app.stores.get(self.store)
