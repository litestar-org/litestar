from litestar import Litestar, Response, get
from litestar.datastructures import Cookie, ResponseHeader


@get(
    "/static",
    response_headers=[ResponseHeader(name="my-header", value="header-value")],
    response_cookies=[Cookie(key="my-cookie", value="cookie-value")],
    sync_to_thread=False,
)
def static() -> str:
    # you can set headers and cookies when defining handlers
    return "hello"


@get("/dynamic", sync_to_thread=False)
def dynamic() -> Response[str]:
    # or dynamically, by returning an instance of Response
    return Response(
        "hello",
        headers={"my-header": "header-value"},
        cookies=[Cookie(key="my-cookie", value="cookie-value")],
    )


app = Litestar([static, dynamic])

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_static_sets_header_and_cookie() -> None:
    with TestClient(app) as client:
        response = client.get("/static")
        assert response.status_code == HTTP_200_OK
        assert response.headers["my-header"] == "header-value"
        assert response.cookies["my-cookie"] == "cookie-value"


def test_dynamic_sets_header_and_cookie() -> None:
    with TestClient(app) as client:
        response = client.get("/dynamic")
        assert response.status_code == HTTP_200_OK
        assert response.headers["my-header"] == "header-value"
        assert response.cookies["my-cookie"] == "cookie-value"
