from litestar import get, Litestar


@get(["/", "/sub-path"])
def handler() -> None: ...


app = Litestar(route_handlers=[handler])