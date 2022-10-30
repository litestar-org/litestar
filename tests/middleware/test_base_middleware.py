from typing import TYPE_CHECKING, Any

from starlette.datastructures import MutableHeaders

from starlite import AbstractMiddleware, DefineMiddleware, ValidationException, get
from starlite.status_codes import HTTP_400_BAD_REQUEST
from starlite.testing import create_test_client

if TYPE_CHECKING:

    from starlite.types import Message, Receive, Scope, Send


def test_custom_middleware() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers.append("test", str(123))
                await send(message)

            await self.app(scope, receive, _send)

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert response.headers["test"] == "123"


def test_raises_exception() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            raise ValidationException(detail="nope")

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_exclude_by_pattern() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        def __init__(self, **kwargs: Any) -> None:
            kwargs.update(exclude="route-123")
            super().__init__(**kwargs)

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers.append("test", str(123))
                await send(message)

            await self.app(scope, receive, _send)

    @get("/route-123")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert "test" not in response.headers


def test_exclude_by_opt_key() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        def __init__(self, **kwargs: Any) -> None:
            kwargs.update(exclude_opt_key="exclude_route")
            super().__init__(**kwargs)

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers.append("test", str(123))
                await send(message)

                await self.app(scope, receive, _send)

    @get("/", exclude_route=True)
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert "test" not in response.headers
