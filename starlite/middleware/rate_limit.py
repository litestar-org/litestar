import re
from time import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Tuple,
    cast,
)

from orjson import dumps, loads
from pydantic import BaseModel

from starlite.connection import Request
from starlite.enums import ScopeType
from starlite.exceptions.exceptions import TooManyRequestsException
from starlite.middleware.base import DefineMiddleware

if TYPE_CHECKING:
    from starlite.cache import Cache
    from starlite.types import ASGIApp, Receive, Scope, Send

DurationUnit = Literal["second", "minute", "hour", "day"]

DURATION_VALUES: Dict[DurationUnit, int] = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


class ThrottleConfig(BaseModel):
    excluded_paths: Optional[List[str]]
    rate_limit: Tuple[DurationUnit, int]

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one
        of the application layers.

        Examples:

            ```python
            from starlite import Starlite, Request, get
            from starlite.middleware import ThrottleConfig

            # limit to 10 requests per minute, excluding the schema path
            throttle_config = ThrottleConfig(rate_limit=("minute", 10), excluded_paths=["/schema"])


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
    __slots__ = ("app", "excluded_paths", "cache", "rate_limit_unit", "max_requests")

    cache: "Cache"

    def __init__(
        self, app: "ASGIApp", rate_limit: Tuple[DurationUnit, int], excluded_paths: Optional[List[str]] = None
    ) -> None:
        self.app = app
        self.rate_limit_unit: DurationUnit = rate_limit[0]
        self.max_requests: int = rate_limit[1]
        self.excluded_paths: Optional[Pattern[str]] = re.compile("|".join(excluded_paths)) if excluded_paths else None

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
            while history[-1] <= int(time()) - duration:
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
            if self.should_check_request(request=request):
                key = self.cache_key_from_request(request=request)
                cached_history = await self.retrieve_cached_history(key)
                if len(cached_history) < self.max_requests:
                    raise TooManyRequestsException()
                await self.set_cached_history(key=key, cached_history=cached_history)

        await self.app(scope, receive, send)

    def should_check_request(self, request: "Request[Any, Any]") -> bool:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            Boolean dictating whether the request should be checked for rate-limiting.
        """
        return not self.excluded_paths or not self.excluded_paths.findall(request.url.path)
