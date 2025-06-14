from litestar import Litestar, MediaType, get
from litestar.middleware.rate_limit import RateLimitConfig


@get(
    "/",
    media_type=MediaType.TEXT,
    sync_to_thread=False,
    middleware=[RateLimitConfig(rate_limit=("minute", 1)).middleware],
)
def handler() -> str:
    """Handler which should not be accessed more than once per minute."""
    return "ok"


app = Litestar(route_handlers=[handler])
