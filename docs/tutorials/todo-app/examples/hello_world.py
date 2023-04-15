from litestar import Litestar, get

__all__ = ["hello_world"]


@get("/")
async def hello_world() -> str:
    return "Hello, world!"


app = Litestar([hello_world])
