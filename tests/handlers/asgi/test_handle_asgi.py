from starlette.status import HTTP_200_OK
from starlette.types import Receive, Scope, Send

from starlite import Controller, MediaType, Response, asgi
from starlite.testing import create_test_client


def test_handle_asgi() -> None:
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
