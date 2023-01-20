from typing import Any, Dict

from starlite import Starlite, get


@get("/")
def hello_world(optional_dependency: int = 3) -> Dict[str, Any]:
    """Notice we haven't provided the dependency to the route.

    This is OK, because of the default value, but the parameter shows in the docs.
    """
    return {"hello": optional_dependency}


app = Starlite(route_handlers=[hello_world])
