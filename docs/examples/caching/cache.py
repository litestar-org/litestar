from litestar import Litestar, get
from litestar.config.response_cache import CACHE_FOREVER


@get("/cached", cache=True)
async def my_cached_handler() -> str:
    return "cached"


@get("/cached-seconds", cache=120)  # seconds
async def my_cached_handler_seconds() -> str:
    return "cached for 120 seconds"


@get("/cached-forever", cache=CACHE_FOREVER)
async def my_cached_handler_forever() -> str:
    return "cached forever"


app = Litestar(
    [my_cached_handler, my_cached_handler_seconds, my_cached_handler_forever],
)
