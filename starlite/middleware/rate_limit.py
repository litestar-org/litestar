import re
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
    cast,
)

from orjson import dumps, loads
from pydantic import BaseModel, validator
from typing_extensions import Literal

from starlite.connection import Request
from starlite.enums import ScopeType
from starlite.exceptions.exceptions import TooManyRequestsException
from starlite.middleware.base import DefineMiddleware
from starlite.types import SyncOrAsyncUnion
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from starlite.cache import Cache
    from starlite.types import ASGIApp, Receive, Scope, Send

DurationUnit = Literal["second", "minute", "hour", "day"]

DURATION_VALUES: Dict[DurationUnit, int] = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


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
    set_rate_limit_headers: bool = True
    """Boolean dictating whether to set the rate limit headers on the response.
    """
    rate_limit_remaining_header_key = "X-RateLimit-Remaining"
    """Key to use for the rate limit remaining header"""
    rate_limit_reset_header_key = "X-RateLimit-Reset"
    """Key to use for the rate limit reset header"""
    rate_limit_limit_header_key = "X-RateLimit-Limit"
    """Key to use for the rate limit limit header"""

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
        return DefineMiddleware(ThrottleMiddleware, config=self)


class ThrottleMiddleware:
    __slots__ = (
        "app",
        "cache",
        "check_throttle_handler",
        "exclude",
        "max_requests",
        "rate_limit_limit_header_key",
        "rate_limit_remaining_header_key",
        "rate_limit_reset_header_key",
        "rate_limit_unit",
        "request_quota",
        "set_rate_limit_headers",
    )

    cache: "Cache"

    def __init__(self, app: "ASGIApp", config: RateLimitConfig) -> None:
        """

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of RateLimitConfig.
        """
        self.app = app
        self.check_throttle_handler = config.check_throttle_handler
        self.exclude: Optional[Pattern[str]] = re.compile("|".join(config.exclude)) if config.exclude else None
        self.max_requests: int = config.rate_limit[1]
        self.rate_limit_limit_header_key = config.rate_limit_limit_header_key
        self.rate_limit_remaining_header_key = config.rate_limit_remaining_header_key
        self.rate_limit_reset_header_key = config.rate_limit_reset_header_key
        self.rate_limit_unit: DurationUnit = config.rate_limit[0]
        self.set_rate_limit_headers = config.set_rate_limit_headers

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
                self.cache = cast("Cache", scope["app"].cache)

            request = Request[Any, Any](scope)
            if await self.should_check_request(request=request):
                key = self.cache_key_from_request(request=request)
                cached_history = await self.retrieve_cached_history(key)
                if len(cached_history) >= self.max_requests:
                    raise TooManyRequestsException()
                await self.set_cached_history(key=key, cached_history=cached_history)

        await self.app(scope, receive, send)

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

    async def retrieve_cached_history(self, key: str) -> List[int]:
        """Retrieves a list of time stamps for the given duration unit.

        Args:
            key: Cache key.

        Returns:
            A list of timestamps.
        """
        cached_string = await self.cache.get(key)
        if cached_string:
            history = cast("List[int]", loads(cached_string))
            duration = DURATION_VALUES[self.rate_limit_unit]
            while history and history[-1] <= int(time()) - duration:
                history.pop()
            return history
        return []

    async def set_cached_history(self, key: str, cached_history: List[int]) -> None:
        """Stores history extended with the current timestamp in cache.

        Args:
            key: Cache key.
            cached_history: A list of cached timestamps.

        Returns:
        """
        await self.cache.set(key, dumps([int(time()), *cached_history]))

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

    def create_response_headers(self, history: List[int]) -> Dict[str, str]:
        """
        Creates response headers following the [IETF draft specification for
        RateLimit fields][https://www.ietf.org/id/draft-ietf-httpapi-ratelimit-headers-05.html].
        Args:
            history: History of API calls to the endpoint from the given host.

        Returns:
            A dict of http headers.
        """
        remaining_requests = len(history) - self.max_requests if len(history) <= self.max_requests else 0

        return {
            self.rate_limit_limit_header_key: f"{self.max_requests}; w={DURATION_VALUES[self.rate_limit_unit]}",
            self.rate_limit_remaining_header_key: remaining_requests,
            self.rate_limit_reset_header_key: "",
        }
