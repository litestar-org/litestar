from litestar import get, Litestar


@get("/")
async def handler() -> str:
    return "Hello, world!"


app = Litestar()
app.register(handler)