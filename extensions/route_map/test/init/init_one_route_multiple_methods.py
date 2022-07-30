from typing import List

from starlite import Starlite, delete, get, post
from starlite.routes import BaseRoute  # noqa: TC001

path = "/test"
paths = [path]


@get(path=path)
def handler_fn_get(a: int = 0, b: int = 0, c: int = 0, d: int = 0, e: int = 0) -> None:
    ...


@post(path=path)
def handler_fn_post(a: int = 0, b: int = 0, c: int = 0, d: int = 0, e: int = 0) -> None:
    ...


@delete(path=path)
def handler_fn_delete(a: int = 0, b: int = 0, c: int = 0, d: int = 0, e: int = 0) -> None:
    ...


app = Starlite(route_handlers=[handler_fn_get, handler_fn_post, handler_fn_delete])
routes: List[BaseRoute] = []

for app_route in app.routes:
    if app_route.path in paths:
        routes.append(app_route)
