from typing import List

from starlite import Starlite, delete, get, post
from starlite.routes import BaseRoute  # noqa: TC001

path = "/test/{val:int}"
paths = [path]


@get(path=path)
def handler_fn_get(val: int) -> None:
    ...


@post(path=path)
def handler_fn_post(val: int) -> None:
    ...


@delete(path=path)
def handler_fn_delete(val: int) -> None:
    ...


app = Starlite(route_handlers=[handler_fn_get, handler_fn_post, handler_fn_delete])
routes: List[BaseRoute] = []

for app_route in app.routes:
    if app_route.path in paths:
        routes.append(app_route)
