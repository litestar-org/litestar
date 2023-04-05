from typing import Dict

from litestar import Litestar, get


@get("/")
def hello_world() -> Dict[str, str]:
    """Handler function that returns a greeting dictionary."""
    return {"hello": "world"}


app = Litestar(route_handlers=[hello_world])

# run: /
