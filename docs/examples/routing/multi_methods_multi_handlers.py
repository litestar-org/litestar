from litestar import get, post, Litestar


@get("/")
async def get_handler() -> str:
    return "Hello from get"


@post("/")
async def post_handler() -> str:
    return "Hello from post"


app = Litestar(route_handlers=[get_handler, post_handler])


# run: /
# run: / -X POST
