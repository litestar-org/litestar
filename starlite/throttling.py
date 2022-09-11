import re
from asyncio import get_running_loop
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

from starlite.exceptions.exceptions import TooManyRequestsException

if TYPE_CHECKING:
    from starlite.cache import Cache
    from starlite.connection import Request

DurationUnit = Literal["second", "minute", "hour", "day"]

DURATION_VALUES: Dict[DurationUnit, int] = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


class BaseThrottle:
    __slots__ = ("excluded_paths", "_exclude_re", "cache", "limit")

    cache: "Cache"
    excluded_paths: Optional[List[str]]
    rate_limits: Tuple[DurationUnit, int]

    def __init__(self) -> None:
        self._exclude_re: Optional[Pattern[str]] = None

        if hasattr(self, "excluded_paths") and self.excluded_paths:
            self._exclude_re = re.compile("|".join(self.excluded_paths))

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

    @property
    def now(self) -> int:
        """

        Returns:
            Returns the current timestamp from asyncio
        """
        loop = get_running_loop()
        return int(loop.time())

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
            unit = self.rate_limits[0]
            duration = DURATION_VALUES[unit]
            while history[-1] <= self.now - duration:
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
        await self.cache.set(key, dumps([self.now, *cached_history]))

    async def __call__(self, request: "Request[Any, Any]", opt: Dict[str, Any]) -> None:
        if not hasattr(self, "cache"):
            self.cache = request.app.cache
        if self.should_check_request(request=request):
            key = self.cache_key_from_request(request=request)
            cached_history = await self.retrieve_cached_history(key)
            self.check_request(request=request, opt=opt, cached_history=cached_history)
            await self.set_cached_history(key=key, cached_history=cached_history)

    def should_check_request(self, request: "Request[Any, Any]") -> bool:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.

        Returns:
            Boolean dictating whether the request should be checked for rate-limiting.
        """
        return not self._exclude_re or not self._exclude_re.findall(request.url.path)

    def check_request(  # pylint: disable=unused-argument
        self,
        request: "Request[Any, Any]",
        opt: Dict[str, Any],
        cached_history: List[int],
    ) -> None:
        """

        Args:
            request: A [Request][starlite.connection.Request] instance.
            opt: The 'opt' dictionary defined on the route handler, if any.
            cached_history: A list of timestamps recording the timestamps in the given duration timeframe.

        Raises:
            TooManyRequestsException: if the request limits have been exceeded.
        """
        max_requests = self.rate_limits[1]
        if len(cached_history) < max_requests:
            raise TooManyRequestsException()
