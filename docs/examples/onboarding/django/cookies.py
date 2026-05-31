from litestar import Litestar, Response, get
from litestar.datastructures import Cookie


@get("/static", response_cookies=[Cookie(key="my-cookie", value="cookie-value")])
async def static_cookie() -> dict[str, str]:
    return {"set": "static"}


@get("/dynamic")
async def dynamic_cookie() -> Response[dict[str, str]]:
    return Response(
        {"set": "dynamic"},
        cookies=[Cookie(key="my-cookie", value="cookie-value")],
    )


app = Litestar(route_handlers=[static_cookie, dynamic_cookie])
