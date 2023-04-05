from starlite import Starlite
from starlite.stores.redis import RedisStore

root_store = RedisStore.with_client()
cache_store = root_store.with_namespace("cache")
session_store = root_store.with_namespace("sessions")


async def before_shutdown() -> None:
    await cache_store.delete_all()


app = Starlite(before_shutdown=[before_shutdown])
