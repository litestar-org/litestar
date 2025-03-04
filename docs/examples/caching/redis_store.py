import asyncio

from litestar import Litestar, get
from litestar.config.response_cache import ResponseCacheConfig
from litestar.stores.redis import RedisStore


@get(cache=10)
async def something() -> str:
    await asyncio.sleep(1)
    return "something"


redis_store = RedisStore.with_client(url="redis://localhost/", port=6379, db=0)
cache_config = ResponseCacheConfig(store="redis_backed_store")
app = Litestar(
    [something],
    stores={"redis_backed_store": redis_store},
    response_cache_config=cache_config,
)
