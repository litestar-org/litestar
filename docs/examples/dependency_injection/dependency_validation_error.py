from typing import Any, Dict

from litestar import Litestar, get
from litestar.di import NamedDependency, Provide


async def provide_str() -> str:
    """Returns a string."""
    return "whoops"


@get("/", dependencies={"injected": Provide(provide_str)}, sync_to_thread=False)
def hello_world(injected: NamedDependency[int]) -> Dict[str, Any]:
    """Handler expects an `int`, but we've provided a `str`."""
    return {"hello": injected}


app = Litestar(route_handlers=[hello_world])
