from litestar import Litestar, Response, get
from litestar.datastructures import Cookie


@get(
    "/static",
    response_headers={"my-header": "header-value"},
    response_cookies=[Cookie(key="my-cookie", value="cookie-value")],
    sync_to_thread=False,
)
def static() -> str:
    return "hello"


@get("/dynamic", sync_to_thread=False)
def dynamic() -> Response[str]:
    return Response(
        "hello",
        headers={"my-header": "header-value"},
        cookies=[Cookie(key="my-cookie", value="cookie-value")],
    )


app = Litestar(route_handlers=[static, dynamic])
