from litestar import get


@get("/b")
def func() -> None:
    pass
    # b.func
