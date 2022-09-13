import re
from time import time
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
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


class ThrottleConfig(BaseModel):
    rate_limit: Tuple[DurationUnit, int]
    """A tuple containing a time unit (second, minute, hour, day) and quantity, e.g. ("day", 1) or ("minute", 5)"""
    exclude: Optional[List[str]] = None
    """Optional list of patterns to skip in the authentication middleware."""
    check_throttle_handler: Optional[Callable[[Request[Any, Any]], SyncOrAsyncUnion[bool]]] = None
    """
    Optional handler callable that receives the request instance, returning a boolean dictating whether or not the
    request should be checked for rate limiting.
    """

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
            from starlite.middleware import ThrottleConfig

            # limit to 10 requests per minute, excluding the schema path
            throttle_config = ThrottleConfig(rate_limit=("minute", 10), exclude=["/schema"])


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[throttle_config.middleware])
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(ThrottleMiddleware, **self.dict())


class ThrottleMiddleware:
    __slots__ = ("app", "exclude", "cache", "rate_limit_unit", "max_requests", "check_throttle_handler")

    cache: "Cache"

    def __init__(
        self,
        app: "ASGIApp",
        rate_limit: Tuple[DurationUnit, int],
        exclude: Optional[List[str]] = None,
        check_throttle_handler: Optional[Callable[[Request[Any, Any]], Awaitable[bool]]] = None,
    ) -> None:
        """

        Args:
            app: The 'next' ASGI app to call.
            rate_limit: A tuple containing a time unit.
            exclude: A pattern or list of patterns to skip in the authentication middleware.
        """
        self.app = app
        self.check_throttle_handler = check_throttle_handler
        self.exclude: Optional[Pattern[str]] = re.compile("|".join(exclude)) if exclude else None
        self.max_requests: int = rate_limit[1]
        self.rate_limit_unit: DurationUnit = rate_limit[0]

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
