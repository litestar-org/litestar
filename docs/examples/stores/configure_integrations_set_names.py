from pathlib import Path

from litestar import Litestar
from litestar.config.response_cache import ResponseCacheConfig
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.file import FileStore
from litestar.stores.redis import RedisStore

app = Litestar(
    stores={"redis": RedisStore.with_client(), "file": FileStore(Path("data"))},
    response_cache_config=ResponseCacheConfig(store="redis"),
    middleware=[
        ServerSideSessionConfig(store="file").middleware,
        RateLimitConfig(rate_limit=("second", 10), store="redis").middleware,
    ],
)
