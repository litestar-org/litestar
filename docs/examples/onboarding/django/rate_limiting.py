from litestar import Litestar, MediaType, get
from litestar.middleware.rate_limit import RateLimitConfig

rate_limit_config = RateLimitConfig(rate_limit=("minute", 60), exclude=["/schema"])


@get("/", media_type=MediaType.TEXT)
async def handler() -> str:
    return "ok"


app = Litestar(
    route_handlers=[handler],
    middleware=[rate_limit_config.middleware],
)
