from typing import Annotated, Any

from litestar import Litestar, get
from litestar.di import Provide
from litestar.params import Dependency


async def provide_str() -> str:
    """Returns a string."""
    return "whoops"


@get("/", dependencies={"injected": Provide(provide_str)}, sync_to_thread=False)
def hello_world(injected: Annotated[int, Dependency(skip_validation=True)]) -> dict[str, Any]:
    """Handler expects an `int`, but we've provided a `str`."""
    return {"hello": injected}


app = Litestar(route_handlers=[hello_world])
