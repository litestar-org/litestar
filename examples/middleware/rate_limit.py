from starlite import Starlite, get
from starlite.middleware import RateLimitConfig

rate_limit_config = RateLimitConfig(rate_limit=("minute", 1), exclude=["/schema"])


@get("/")
def handler() -> str:
    """Handler which should not be accessed more than once per minute."""
    return "ok"


app = Starlite(route_handlers=[handler], middleware=[rate_limit_config.middleware])
