from typing import Any, Dict

from litestar import Litestar, get
from litestar.di import NamedDependency
from litestar.params import SkipValidation


async def provide_str() -> str:
    """Returns a string."""
    return "whoops"


@get("/", dependencies={"injected": provide_str})
async def hello_world(injected: NamedDependency[SkipValidation[int]]) -> Dict[str, Any]:
    """Handler expects an `int`, but we've provided a `str`."""
    return {"hello": injected}


app = Litestar(route_handlers=[hello_world])
