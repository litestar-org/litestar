from typing import Any

from litestar import Litestar, MediaType, get
from litestar.connection.request import Request
from litestar.middleware.rate_limit import RateLimitConfig, RateLimitMiddleware


class EndpointRateLimitMiddleware(RateLimitMiddleware):
    def cache_key_from_request(self, request: Request[Any, Any, Any]) -> str:
        identifier = request.scope["path"]
        return f"{type(self).__name__}::{identifier}"


rate_limit_config = RateLimitConfig(rate_limit=("minute", 1))


@get("/one", media_type=MediaType.TEXT, sync_to_thread=False)
def one() -> None:
    return None


@get("/two", sync_to_thread=False)
def two() -> None:
    return None


app = Litestar(route_handlers=[one, two], middleware=[rate_limit_config.middleware])
