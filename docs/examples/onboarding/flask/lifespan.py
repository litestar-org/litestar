from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from litestar import Litestar, get


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncIterator[None]:
    # Setup: open database pool, warm caches, etc.
    yield
    # Teardown: close resources.


@get("/")
async def index() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(route_handlers=[index], lifespan=[lifespan])
