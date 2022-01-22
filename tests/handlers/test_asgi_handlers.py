import pytest
from starlette.status import HTTP_200_OK
from starlette.types import Receive, Scope, Send

from starlite import (
    Controller,
    ImproperlyConfiguredException,
    MediaType,
    Response,
    asgi,
    create_test_client,
)


def test_asgi_handler_validation():
    def fn_without_scope_arg(receive: Receive, send: Send) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_without_scope_arg)

    def fn_without_receive_arg(scope: Scope, send: Send) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_without_receive_arg)

    def fn_without_send_arg(scope: Scope, receive: Receive) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_without_send_arg)

    def fn_with_return_annotation(scope: Scope, receive: Receive, send: Send) -> dict:
        return dict()

    with pytest.raises(ImproperlyConfiguredException):
        asgi(path="/")(fn_with_return_annotation)

    asgi_handler_with_no_fn = asgi(path="/")

    with pytest.raises(ImproperlyConfiguredException):
        create_test_client(route_handlers=asgi_handler_with_no_fn)


def test_handle_asgi():
    @asgi(path="/")
    async def root_asgi_handler(scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "http"
        assert scope["method"] == "GET"
        response = Response("Hello World", media_type=MediaType.TEXT, status_code=HTTP_200_OK)
        await response(scope, receive, send)

    class MyController(Controller):
        path = "/asgi"

        @asgi()
        async def root_asgi_handler(self, scope: Scope, receive: Receive, send: Send) -> None:
            assert scope["type"] == "http"
            assert scope["method"] == "GET"
            response = Response("Hello World", media_type=MediaType.TEXT, status_code=HTTP_200_OK)
            await response(scope, receive, send)

    with create_test_client([root_asgi_handler, MyController]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello World"
        response = client.get("/asgi")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello World"
