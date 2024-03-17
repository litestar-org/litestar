from typing import Any, Dict

from litestar import Litestar, get


@get("/", sync_to_thread=False)
def hello_world(optional_dependency: int = 3) -> Dict[str, Any]:
    """Notice we have not provided the dependency to the route.

    This is OK, because of the default value, but the parameter shows in the docs.
    """
    return {"hello": optional_dependency}


app = Litestar(route_handlers=[hello_world])
