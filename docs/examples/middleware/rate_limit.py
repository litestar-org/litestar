from litestar import Litestar, MediaType, get
from litestar.middleware.rate_limit import RateLimitConfig

rate_limit_config = RateLimitConfig(
    rate_limit=[("second", 1), ("minute", 10)],
    exclude=["/schema"],
)


@get("/", media_type=MediaType.TEXT, sync_to_thread=False)
def handler() -> str:
    """Handler limited by both the per-second and per-minute windows."""
    return "ok"


app = Litestar(route_handlers=[handler], middleware=[rate_limit_config.middleware])
