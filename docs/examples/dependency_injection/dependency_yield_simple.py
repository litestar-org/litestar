from collections.abc import AsyncGenerator

from litestar import Litestar, get
from litestar.di import NamedDependency, Provide

CONNECTION = {"open": False}


async def generator_function() -> AsyncGenerator[dict[str, bool], None]:
    """Set connection to open and close it after the handler returns."""
    CONNECTION["open"] = True
    yield CONNECTION
    CONNECTION["open"] = False


@get("/", dependencies={"conn": Provide(generator_function)})
def index(conn: NamedDependency[dict[str, bool]]) -> dict[str, bool]:
    """Return the current connection state."""
    return conn


app = Litestar(route_handlers=[index])
