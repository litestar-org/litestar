from datetime import datetime, timedelta

from litestar import Litestar, Request
from litestar.stores.memory import MemoryStore

memory_store = MemoryStore()


async def after_response(request: Request) -> None:
    now = datetime.utcnow()
    last_cleared = request.app.state.get("store_last_cleared", now)
    if datetime.utcnow() - last_cleared > timedelta(seconds=30):
        await memory_store.delete_expired()
    app.state["store_last_cleared"] = now


app = Litestar(after_response=after_response)
