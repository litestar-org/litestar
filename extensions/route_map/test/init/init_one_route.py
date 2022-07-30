from typing import List

from starlite import Starlite, get
from starlite.routes import BaseRoute  # noqa: TC001

path = "/test"
paths = [path]


@get(path=path)
def handler_fn(a: int = 0, b: int = 0, c: int = 0, d: int = 0, e: int = 0) -> None:
    ...


app = Starlite(route_handlers=[handler_fn])
routes: List[BaseRoute] = []

for app_route in app.routes:
    if app_route.path in paths:
        routes.append(app_route)
