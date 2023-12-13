from litestar import get


@get("/a")
def func() -> None:
    pass
    # a.func
