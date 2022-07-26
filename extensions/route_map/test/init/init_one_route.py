from starlite import Starlite, get

path = "/test"


@get(path=path)
def handler_fn(a: int = 0, b: int = 0, c: int = 0, d: int = 0, e: int = 0) -> None:
    ...


app = Starlite(route_handlers=[handler_fn])
route = app.routes[0]
