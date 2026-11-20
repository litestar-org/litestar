from litestar import Litestar, asgi, get


@get("/")
async def index() -> str:
    return "Hello from the mounted app"


mounted_app = Litestar(route_handlers=[index])

app = Litestar(
    route_handlers=[asgi(path="/some/sub-path", is_mount=True)(mounted_app)],
    lifespan=[lambda _: mounted_app.lifespan()],
)
