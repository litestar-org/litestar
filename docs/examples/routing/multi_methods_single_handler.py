from litestar import route, Litestar, Request


@route("/", http_method=["GET", "POST"])
async def handler(request: Request) -> str:
    if request.method == "GET":
        return "Hello from get"
    return "Hello from post"


app = Litestar(route_handlers=[handler])


# run: /
# run: / -X POST
