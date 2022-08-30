"""Minimal Starlite application."""
from starlite import Starlite, get


@get("/")
def hello_world() -> dict[str, str]:
    """Hi."""
    return {"hello": "world"}


app = Starlite(route_handlers=[hello_world])
