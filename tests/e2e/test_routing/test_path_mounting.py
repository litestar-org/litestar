from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch

from litestar import Litestar, MediaType, Router, asgi, get, websocket
from litestar.connection import WebSocket
from litestar.exceptions import ImproperlyConfiguredException, WebSocketDisconnect
from litestar.params import FromPath
from litestar.response.base import ASGIResponse
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.handlers import ASGIRouteHandler
    from litestar.types import Receive, Scope, Send


def test_supports_mounting() -> None:
    @asgi("/base/sub/path", is_mount=True)
    async def asgi_handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=scope["path"].encode(), media_type=MediaType.TEXT)
        await response(scope, receive, send)

    @asgi("/sub/path", is_mount=True)
    async def asgi_handler_mount_path(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=scope["path"].encode(), media_type=MediaType.TEXT)
        await response(scope, receive, send)

    @asgi("/not/mount")
    async def asgi_handler_not_mounted_path(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=scope["path"].encode(), media_type=MediaType.TEXT)
        await response(scope, receive, send)

    with create_test_client(
        route_handlers=[asgi_handler, asgi_handler_mount_path, asgi_handler_not_mounted_path]
    ) as client:
        response = client.get("/base/sub/path")
        assert response.status_code == HTTP_200_OK
        assert response.text == "/"

        response = client.get("/base/sub/path/abcd")
        assert response.status_code == HTTP_200_OK
        assert response.text == "/abcd/"

        response = client.get("/base/sub/path/abcd/complex/123/terminus")
        assert response.status_code == HTTP_200_OK
        assert response.text == "/abcd/complex/123/terminus/"

        response = client.get("/sub/path/deep/path")
        assert response.status_code == HTTP_200_OK
        assert response.text == "/deep/path/"

        response = client.get("/not/mount")
        assert response.status_code == HTTP_200_OK
        assert response.text == "/not/mount"


def _mount(path: str) -> "ASGIRouteHandler":
    @asgi(path, is_mount=True)
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=f"{path} {scope['path']}".encode(), media_type=MediaType.TEXT)
        await response(scope, receive, send)

    return handler


def test_mount_does_not_match_partial_path_segment() -> None:
    with create_test_client(route_handlers=[_mount("/admin")]) as client:
        assert client.get("/admin/users").text == "/admin /users/"
        assert client.get("/administrator").status_code == HTTP_404_NOT_FOUND
        assert client.get("/admin-panel").status_code == HTTP_404_NOT_FOUND


def test_mount_under_router_does_not_match_partial_path_segment() -> None:
    with create_test_client(route_handlers=[Router("/api", route_handlers=[_mount("/admin")])]) as client:
        assert client.get("/api/admin/users").text == "/admin /users/"
        assert client.get("/api/administrator").status_code == HTTP_404_NOT_FOUND


def test_mount_does_not_match_partial_path_segment_for_websocket() -> None:
    @asgi("/admin", is_mount=True)
    async def mount(scope: "Scope", receive: "Receive", send: "Send") -> None:
        socket: WebSocket = WebSocket(scope, receive=receive, send=send)
        await socket.accept()
        await socket.send_text(scope["path"])
        await socket.close()

    with create_test_client(route_handlers=[mount]) as client:
        with client.websocket_connect("/admin/socket") as ws:
            assert ws.receive_text() == "/socket/"

        with pytest.RaisesGroup(pytest.RaisesExc(WebSocketDisconnect)), client.websocket_connect("/administrator"):
            pass


def test_mount_prefix_sibling_is_reachable() -> None:
    with create_test_client(route_handlers=[_mount("/a"), _mount("/ab")]) as client:
        assert client.get("/ab").text == "/ab /"
        assert client.get("/ab/x").text == "/ab /x/"
        assert client.get("/a/x").text == "/a /x/"
        assert client.get("/abc").status_code == HTTP_404_NOT_FOUND


def test_nested_mounts() -> None:
    with create_test_client(route_handlers=[_mount("/a"), _mount("/a/b")]) as client:
        assert client.get("/a/b").text == "/a/b /"
        assert client.get("/a/b/c").text == "/a/b /c/"
        assert client.get("/a/bc").text == "/a /bc/"


@pytest.mark.parametrize(
    ("mount_path", "near_miss"),
    [("/foo.bar", "/fooxbar"), ("/g(h", "/gh"), ("/a|b", "/a")],
)
def test_mount_path_with_regex_metacharacters(mount_path: str, near_miss: str) -> None:
    with create_test_client(route_handlers=[_mount(mount_path)]) as client:
        assert client.get(mount_path).status_code == HTTP_200_OK
        assert client.get(near_miss).status_code == HTTP_404_NOT_FOUND


def test_root_mount_does_not_shadow_other_mounts() -> None:
    with create_test_client(route_handlers=[_mount("/"), _mount("/admin")]) as client:
        assert client.get("/admin").text == "/admin /"
        assert client.get("/admin/x").text == "/admin /x/"
        # the root mount's scope path lacks a leading slash - pre-existing, unrelated to the boundary
        assert client.get("/other").text.startswith("/ ")


def test_parametrized_handler_sharing_a_prefix_with_a_mount() -> None:
    @get("/administrator/{user_id:int}")
    async def regular_handler(user_id: FromPath[int]) -> int:
        return user_id

    with create_test_client(route_handlers=[_mount("/admin"), regular_handler]) as client:
        assert client.get("/administrator/7").json() == 7
        assert client.get("/admin/7").text == "/admin /7/"


def test_supports_sub_routes_below_asgi_handlers() -> None:
    @asgi("/base/sub/path")
    async def asgi_handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=scope["path"].encode(), media_type=MediaType.TEXT)
        await response(scope, receive, send)

    @get("/base/sub/path/abc")
    def regular_handler() -> None:
        return

    assert Litestar(route_handlers=[asgi_handler, regular_handler])


def test_does_not_support_asgi_handlers_on_same_level_as_regular_handlers() -> None:
    @asgi("/base/sub/path")
    async def asgi_handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=scope["path"].encode(), media_type=MediaType.TEXT)
        await response(scope, receive, send)

    @get("/base/sub/path")
    def regular_handler() -> None:
        return

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[asgi_handler, regular_handler])


def test_does_not_support_asgi_handlers_on_same_level_as_websockets() -> None:
    @asgi("/base/sub/path")
    async def asgi_handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=scope["path"].encode(), media_type=MediaType.TEXT)
        await response(scope, receive, send)

    @websocket("/base/sub/path")
    async def regular_handler(socket: "WebSocket") -> None:
        return

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[asgi_handler, regular_handler])


@pytest.mark.parametrize(
    "server_command",
    [
        pytest.param(["uvicorn", "app:app", "--port", "9999"], id="uvicorn"),
        pytest.param(["hypercorn", "app:app", "--bind", "127.0.0.1:9999"], id="hypercorn"),
        pytest.param(["daphne", "app:app", "--port", "9999"], id="daphne"),
    ],
)
@pytest.mark.xdist_group("live_server_test")
@pytest.mark.server_integration
def test_path_mounting_live_server(
    tmp_path: Path, monkeypatch: MonkeyPatch, server_command: list[str], run_server: Callable[[str, list[str]], None]
) -> None:
    app = """
from litestar import asgi, Litestar
from litestar.types import Receive, Scope, Send
from litestar.response.base import ASGIResponse

@asgi("/sub/path", is_mount=True)
async def handler(scope: Scope, receive: Receive, send: Send) -> None:
    response = ASGIResponse(body=scope["path"].encode())
    await response(scope, receive, send)


app = Litestar(route_handlers=[handler])
"""
    run_server(app, server_command)

    res = httpx.get("http://127.0.0.1:9999/sub/path/fragment")
    assert res.status_code == 200
    assert res.text == "/fragment/"
