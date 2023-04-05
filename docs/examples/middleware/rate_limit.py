from litestar import Litestar, MediaType, get
from litestar.middleware.rate_limit import RateLimitConfig

rate_limit_config = RateLimitConfig(rate_limit=("minute", 1), exclude=["/schema"])


@get("/", media_type=MediaType.TEXT)
def handler() -> str:
    """Handler which should not be accessed more than once per minute."""
    return "ok"


app = Litestar(route_handlers=[handler], middleware=[rate_limit_config.middleware])
