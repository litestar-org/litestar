from typing import Dict, Generator

from litestar import Litestar, get
from litestar.di import Provide

CONNECTION = {"open": False}


def generator_function() -> Generator[Dict[str, bool], None, None]:
    """Set connection to open and close it after the handler returns."""
    CONNECTION["open"] = True
    yield CONNECTION
    CONNECTION["open"] = False


@get("/", dependencies={"conn": Provide(generator_function)})
def index(conn: Dict[str, bool]) -> Dict[str, bool]:
    """Return the current connection state."""
    return conn


app = Litestar(route_handlers=[index])
