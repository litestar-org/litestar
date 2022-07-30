from typing import List

from starlite import Starlite, get
from starlite.routes import BaseRoute  # noqa: TC001

path = "/articles/{id:str}"
paths = [path]


@get(path=path)
def handler_fn(id: str) -> None:
    ...


app = Starlite(route_handlers=[handler_fn])
routes: List[BaseRoute] = []

for app_route in app.routes:
    if app_route.path in paths:
        routes.append(app_route)
