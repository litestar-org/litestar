from litestar import Litestar, get


@get("/")
async def index() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(route_handlers=[index])
