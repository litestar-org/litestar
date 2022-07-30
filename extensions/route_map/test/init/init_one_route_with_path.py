from starlite import Starlite, get

path = "/articles/{id:str}"


@get(path=path)
def handler_fn(id: str) -> None:
    ...


app = Starlite(route_handlers=[handler_fn])
route = app.routes[0]
