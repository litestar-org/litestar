from typing import Any

from litestar import Litestar, get
from litestar.di import NamedDependency


@get("/")
async def hello_world(non_optional_dependency: NamedDependency[int]) -> dict[str, Any]:
    """Notice we haven't provided the dependency to the route.

    This is not great, however by explicitly marking dependencies, Litestar won't let the app start.
    """
    return {"hello": non_optional_dependency}


app = Litestar(route_handlers=[hello_world])

# ImproperlyConfiguredException: 500: Explicit dependency 'non_optional_dependency' for 'hello_world' has no default
# value, or provided dependency.
