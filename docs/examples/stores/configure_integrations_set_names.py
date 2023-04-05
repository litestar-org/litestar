from pathlib import Path

from starlite import Starlite
from starlite.config.response_cache import ResponseCacheConfig
from starlite.middleware.rate_limit import RateLimitConfig
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.file import FileStore
from starlite.stores.redis import RedisStore

app = Starlite(
    stores={"redis": RedisStore.with_client(), "file": FileStore(Path("data"))},
    response_cache_config=ResponseCacheConfig(store="redis"),
    middleware=[
        ServerSideSessionConfig(store="file").middleware,
        RateLimitConfig(rate_limit=("second", 10), store="redis").middleware,
    ],
)
