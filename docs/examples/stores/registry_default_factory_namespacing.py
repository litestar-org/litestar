from starlite import Starlite, get
from starlite.middleware.rate_limit import RateLimitConfig
from starlite.middleware.session.server_side import ServerSideSessionConfig
from starlite.stores.redis import RedisStore
from starlite.stores.registry import StoreRegistry

root_store = RedisStore.with_client()


@get(cache=True)
def cached_handler() -> str:
    # this will use app.stores.get("response_cache")
    return "Hello, world!"


app = Starlite(
    [cached_handler],
    stores=StoreRegistry(default_factory=root_store.with_namespace),
    middleware=[
        RateLimitConfig(("second", 1)).middleware,
        ServerSideSessionConfig().middleware,
    ],
)
