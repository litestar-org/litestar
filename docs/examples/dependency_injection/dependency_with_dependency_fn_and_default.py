from typing import Annotated, Any

from typing import Any, Dict

from litestar import Litestar, get
from litestar.di import NamedDependency


@get("/")
async def hello_world(optional_dependency: NamedDependency[int] = 3) -> dict[str, Any]:
    """Notice we haven't provided the dependency to the route.

    This is OK, because of the default value, and now the parameter is excluded from the docs.
    """
    return {"hello": optional_dependency}


app = Litestar(route_handlers=[hello_world])
