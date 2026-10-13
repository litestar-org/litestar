from litestar import Litestar
from litestar.stores.redis import RedisStore

root_store = RedisStore.with_client()
cache_store = root_store.with_namespace("cache")
session_store = root_store.with_namespace("sessions")


async def on_shutdown() -> None:
    await cache_store.delete_all()


app = Litestar(on_shutdown=[on_shutdown])
