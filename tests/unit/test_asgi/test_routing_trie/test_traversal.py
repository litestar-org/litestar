from typing import Any

from litestar import Router, asgi, get
from litestar.response.base import ASGIResponse
from litestar.status_codes import HTTP_404_NOT_FOUND
from litestar.testing import create_test_client


def test_parse_path_to_route_mounted_app_path_root() -> None:
    # test that paths are correctly dispatched to handlers when mounting an app
    # and other handlers to root path /

    @asgi("/foobar", is_mount=True)
    async def mounted_handler(scope: Any, receive: Any, send: Any) -> None:
        response = ASGIResponse(body="mounted")
        await response(scope, receive, send)

    @get("/{number:int}/foobar/")
    async def parametrized_handler() -> str:
        return "parametrized"

    @get("/static/foobar/")
    async def static_handler() -> str:
        return "static"

    with create_test_client(
        [
            mounted_handler,
            parametrized_handler,
            static_handler,
        ]
    ) as client:
        response = client.get("/foobar")
        assert response.text == "mounted"

        response = client.get("/foobar/123/")
        assert response.text == "mounted"

        response = client.get("/123/foobar/")
        assert response.text == "parametrized"

        response = client.get("/static/foobar/")
        assert response.text == "static"

        response = client.get("/unknown/foobar/")
        assert response.status_code == HTTP_404_NOT_FOUND


def test_parse_path_to_route_mounted_app_path_router() -> None:
    # test that paths are correctly dispatched to handlers when mounting an app
    # and other handlers inside subrouter

    @asgi("/foobar", is_mount=True)
    async def mounted_handler(scope: Any, receive: Any, send: Any) -> None:
        response = ASGIResponse(body="mounted")
        await response(scope, receive, send)

    @get("/{number:int}/foobar/")
    async def parametrized_handler() -> str:
        return "parametrized"

    @get("/static/foobar/")
    async def static_handler() -> str:
        return "static"

    sub_router = Router(
        path="/sub",
        route_handlers=[
            mounted_handler,
            parametrized_handler,
            static_handler,
        ],
    )
    base_router = Router(path="/base", route_handlers=[sub_router])

    with create_test_client([base_router]) as client:
        response = client.get("/foobar")
        assert response.status_code == HTTP_404_NOT_FOUND

        response = client.get("/base/sub/foobar")
        assert response.text == "mounted"

        response = client.get("/base/sub/foobar/123/")
        assert response.text == "mounted"

        response = client.get("/base/sub/123/foobar/")
        assert response.text == "parametrized"

        response = client.get("/base/sub/static/foobar/")
        assert response.text == "static"

        response = client.get("/base/sub/unknown/foobar/")
        assert response.status_code == HTTP_404_NOT_FOUND
