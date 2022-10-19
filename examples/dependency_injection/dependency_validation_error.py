from typing import Any

from starlite import Provide, Starlite, get


def provide_str() -> str:
    """Returns a string."""
    return "whoops"


@get("/", dependencies={"injected": Provide(provide_str)})
def hello_world(injected: int) -> dict[str, Any]:
    """Handler expects and `int`, but we've provided a `str`."""
    return {"hello": injected}


app = Starlite(route_handlers=[hello_world])
