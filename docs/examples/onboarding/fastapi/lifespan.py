from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from litestar import Litestar, get


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncIterator[None]:
    # Setup code runs before the application starts accepting requests.
    yield
    # Teardown code runs after the application has stopped.


@get("/")
async def index() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(route_handlers=[index], lifespan=[lifespan])
