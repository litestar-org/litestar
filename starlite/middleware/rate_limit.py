import re
from dataclasses import dataclass
from time import time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Pattern,
    Tuple,
    Type,
    cast,
)

from orjson import dumps, loads
from pydantic import BaseModel, validator
from starlette.datastructures import MutableHeaders
from typing_extensions import Literal

from starlite.connection import Request
from starlite.enums import ScopeType
from starlite.exceptions import TooManyRequestsException
from starlite.middleware.base import DefineMiddleware
from starlite.types import Message, SyncOrAsyncUnion
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from typing import Awaitable

    from starlite.cache import Cache
    from starlite.types import ASGIApp, Receive, Scope, Send

DurationUnit = Literal["second", "minute", "hour", "day"]

DURATION_VALUES: Dict[DurationUnit, int] = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


@dataclass
class CacheObject:
    __slots__ = ("history", "reset")

    history: List[int]
    reset: int


class RateLimitMiddleware:
    __slots__ = (
        "app",
        "cache",
        "check_throttle_handler",
        "exclude",
        "max_requests",
        "unit",
        "request_quota",
        "config",
    )

    cache: "Cache"

    def __init__(self, app: "ASGIApp", config: "RateLimitConfig") -> None:
        """

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of RateLimitConfig.
        """
        self.app = app
        self.check_throttle_handler = cast(
            "Optional[Callable[[Request], Awaitable[bool]]]", config.check_throttle_handler
        )
        self.exclude: Optional[Pattern[str]] = re.compile("|".join(config.exclude)) if config.exclude else None
        self.max_requests: int = config.rate_limit[1]
        self.config = config
        self.unit: DurationUnit = config.rate_limit[0]

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if scope["type"] == ScopeType.HTTP:
            if not hasattr(self, "cache"):
                self.cache = scope["app"].cache

            request: "Request[Any, Any]" = scope["app"].request_class(scope)
            if await self.should_check_request(request=request):
                key = self.cache_key_from_request(request=request)
                cache_object = await self.retrieve_cached_history(key)
                if len(cache_object.history) >= self.max_requests:
                    raise TooManyRequestsException(
                        headers=self.create_response_headers(cache_object=cache_object)
                        if self.config.set_rate_limit_headers
                        else None
                    )
                await self.set_cached_history(key=key, cache_object=cache_object)
                if self.config.set_rate_limit_headers:
                    send = self.create_send_wrapper(send=send, cache_object=cache_object)

        await self.app(scope, receive, send)

    def create_send_wrapper(self, send: "Send", cache_object: CacheObject) -> "Send":
        """Creates a send function that wraps the original send to inject
        response headers.

        Args:
            send: The ASGI send function.
            cache_object: A CacheObject instance.

        Returns:
            Send wrapper callable.
        """

        async def send_wrapper(message: "Message") -> None:
            """

            Args:
                message: An ASGI 'Message'

            Returns:
                None
            """
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                headers = MutableHeaders(scope=message)
                for key, value in self.create_response_headers(cache_object=cache_object).items():
                    headers.append(key, value)
            await send(message)

        return send_wrapper

    def cache_key_from_request(self, request: "Request[Any, Any]") -> str:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            A cache key.
        """
        host = request.client.host if request.client else "anonymous"
        identifier = request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP") or host
        return f"{type(self).__name__}::{identifier}"

    async def retrieve_cached_history(self, key: str) -> CacheObject:
        """Retrieves a list of time stamps for the given duration unit.

        Args:
            key: Cache key.

        Returns:
            An instance of CacheObject.
        """
        duration = DURATION_VALUES[self.unit]
        now = int(time())
        cached_string = await self.cache.get(key)
        if cached_string:
            cache_object = CacheObject(**loads(cached_string))
            if cache_object.reset <= now:
                return CacheObject(history=[], reset=now + duration)

            while cache_object.history and cache_object.history[-1] <= now - duration:
                cache_object.history.pop()
            return cache_object

        return CacheObject(history=[], reset=now + duration)

    async def set_cached_history(self, key: str, cache_object: CacheObject) -> None:
        """Stores history extended with the current timestamp in cache.

        Args:
            key: Cache key.
            cache_object: An instance of CacheObject.

        Returns:
            None
        """
        cache_object.history = [int(time()), *cache_object.history]
        await self.cache.set(key, dumps(cache_object))

    async def should_check_request(self, request: "Request[Any, Any]") -> bool:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            Boolean dictating whether the request should be checked for rate-limiting.
        """
        if not self.exclude or not self.exclude.findall(request.url.path):
            if self.check_throttle_handler:
                return await self.check_throttle_handler(request)
            return True
        return False

    def create_response_headers(self, cache_object: CacheObject) -> Dict[str, str]:
        """Creates ratelimit response headers.

        Notes:
            * see the [IETF RateLimit draft][https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/]

        Args:
            cache_object: An instance of Cache Object.

        Returns:
            A dict of http headers.
        """
        remaining_requests = str(
            len(cache_object.history) - self.max_requests if len(cache_object.history) <= self.max_requests else 0
        )

        return {
            self.config.rate_limit_policy_header_key: f"{self.max_requests}; w={DURATION_VALUES[self.unit]}",
            self.config.rate_limit_limit_header_key: str(self.max_requests),
            self.config.rate_limit_remaining_header_key: remaining_requests,
            self.config.rate_limit_reset_header_key: str(int(time()) - cache_object.reset),
        }


class RateLimitConfig(BaseModel):
    rate_limit: Tuple[DurationUnit, int]
    """A tuple containing a time unit (second, minute, hour, day) and quantity, e.g. ("day", 1) or ("minute", 5)."""
    exclude: Optional[List[str]] = None
    """List of patterns to skip in the authentication middleware."""
    check_throttle_handler: Optional[Callable[[Request[Any, Any]], SyncOrAsyncUnion[bool]]] = None
    """
    Handler callable that receives the request instance, returning a boolean dictating whether or not the
    request should be checked for rate limiting.
    """
    middleware_class: Type[RateLimitMiddleware] = RateLimitMiddleware
    """The middleware class to use."""
    set_rate_limit_headers: bool = True
    """Boolean dictating whether to set the rate limit headers on the response."""
    rate_limit_policy_header_key: str = "RateLimit-Policy"
    """Key to use for the rate limit policy header."""
    rate_limit_remaining_header_key: str = "RateLimit-Remaining"
    """Key to use for the rate limit remaining header."""
    rate_limit_reset_header_key: str = "RateLimit-Reset"
    """Key to use for the rate limit reset header."""
    rate_limit_limit_header_key: str = "RateLimit-Limit"
    """Key to use for the rate limit limit header."""
    cache_key_builder: Optional[Callable[[Request], str]] = None

    @validator("check_throttle_handler")
    def validate_check_throttle_handler(cls, value: Callable) -> Callable:  # pylint: disable=no-self-argument
        """

        Args:
            value: A callable.

        Returns:
            An instance of AsyncCallable
        """
        return AsyncCallable(value)

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one
        of the application layers.

        Examples:

            ```python
            from starlite import Starlite, Request, get
            from starlite.middleware import RateLimitConfig

            # limit to 10 requests per minute, excluding the schema path
            throttle_config = RateLimitConfig(rate_limit=("minute", 10), exclude=["/schema"])


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[throttle_config.middleware])
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(self.middleware_class, config=self)
