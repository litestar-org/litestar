from litestar import Router, get

from .c import C


@get("/r")
def func() -> None:
    pass
    # r.func
    # r.C.func


r = Router(path="/router", route_handlers=[func, C])
