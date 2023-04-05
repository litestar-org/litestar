from typing import Any

from starlite import get
from starlite.params import Dependency


@get("/")
def hello_world(non_optional_dependency: int = Dependency()) -> dict[str, Any]:
    """Notice we haven't provided the dependency to the route.

    This is not great, however by explicitly marking dependencies, Starlite won't let the app start.
    """
    return {"hello": non_optional_dependency}


# app = Starlite(route_handlers=[hello_world])

# ImproperlyConfiguredException: 500: Explicit dependency 'non_optional_dependency' for 'hello_world' has no default
# value, or provided dependency.
