from litestar import Litestar, Response, get


def after_request_app(response: Response) -> Response:
    return Response(content=b"app after request")


def after_request_handler(response: Response) -> Response:
    return Response(content=b"handler after request")


@get("/")
async def handler() -> str:
    return "hello, world"


@get("/override", after_request=after_request_handler)
async def handler_with_override() -> str:
    return "hello, world"


app = Litestar(
    route_handlers=[handler, handler_with_override],
    after_request=after_request_app,
)


# run: /
# run: /override
