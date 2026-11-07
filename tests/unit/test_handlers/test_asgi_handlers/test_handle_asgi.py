from typing import Any
from unittest.mock import MagicMock

import pytest

from litestar import Controller, Litestar, MediaType, asgi
from litestar.enums import ScopeType
from litestar.handlers import ASGIRouteHandler
from litestar.response.base import ASGIResponse
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client
from litestar.types import ASGIApp, Receive, Scope, Send


def test_handle_asgi() -> None:
    @asgi(path="/")
    async def root_asgi_handler(scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == ScopeType.HTTP
        assert scope["method"] == "GET"
        response = ASGIResponse(body=b"Hello World", media_type=MediaType.TEXT)
        await response(scope, receive, send)

    class MyController(Controller):
        path = "/asgi"

        @asgi()
        async def root_asgi_handler(self, scope: Scope, receive: Receive, send: Send) -> None:
            assert scope["type"] == ScopeType.HTTP
            assert scope["method"] == "GET"
            response = ASGIResponse(body=b"Hello World", media_type=MediaType.TEXT)
            await response(scope, receive, send)

    with create_test_client([root_asgi_handler, MyController]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello World"
        response = client.get("/asgi")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello World"


def test_asgi_signature_namespace() -> None:
    class MyController(Controller):
        path = "/asgi"
        signature_namespace = {"b": Receive}

        @asgi(signature_namespace={"c": Send})
        async def root_asgi_handler(
            self,
            scope: "a",  # type:ignore[name-defined]  # noqa: F821
            receive: "b",  # type:ignore[name-defined]  # noqa: F821
            send: "c",  # type:ignore[name-defined]  # noqa: F821
        ) -> None:
            await ASGIResponse(body=scope["path"].encode(), media_type=MediaType.TEXT)(scope, receive, send)

    with create_test_client([MyController], signature_namespace={"a": Scope}) as client:
        response = client.get("/asgi")
        assert response.status_code == HTTP_200_OK
        assert response.text == "/asgi"


def test_custom_handler_class() -> None:
    class MyHandlerClass(ASGIRouteHandler):
        pass

    @asgi("/", handler_class=MyHandlerClass)
    async def handler() -> None:
        pass

    assert isinstance(handler, MyHandlerClass)


@pytest.mark.parametrize(
    "handler_kwargs, expected_value",
    [
        pytest.param({"is_mount": True}, None, id="mount-default"),
        pytest.param({"is_mount": True, "copy_scope": False}, "foo", id="mount-opt-out"),
        pytest.param({}, None, id="non-mount-default"),
        pytest.param({"copy_scope": False}, "foo", id="non-mount-opt-out"),
    ],
)
def test_copy_scope(handler_kwargs: "dict[str, Any]", expected_value: "str | None") -> None:
    mock = MagicMock()

    def middleware_factory(app: Litestar) -> ASGIApp:
        async def middleware(scope: "Scope", receive: "Receive", send: "Send") -> None:
            await app(scope, receive, send)
            mock(scope.get("foo"))

        return middleware

    @asgi(**handler_kwargs)
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        scope["foo"] = "foo"  # type: ignore[typeddict-unknown-key]
        await ASGIResponse()(scope, receive, send)

    with create_test_client([handler], middleware=[middleware_factory]) as client:
        client.get("/")

    mock.assert_called_once_with(expected_value)


def test_copy_scope_isolates_top_level_keys_only() -> None:
    mock = MagicMock()

    def middleware_factory(app: Litestar) -> ASGIApp:
        async def middleware(scope: "Scope", receive: "Receive", send: "Send") -> None:
            await app(scope, receive, send)
            mock(scope.get("foo"), scope["state"].get("injected"))

        return middleware

    @asgi(is_mount=True)
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        scope["foo"] = "foo"  # type: ignore[typeddict-unknown-key]
        scope["state"]["injected"] = "nested"
        await ASGIResponse()(scope, receive, send)

    with create_test_client([handler], middleware=[middleware_factory]) as client:
        client.get("/")

    mock.assert_called_once_with(None, "nested")


def test_copy_scope_default_on_handler_class() -> None:
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None: ...

    assert ASGIRouteHandler(path="/", fn=handler).copy_scope is True
