from typing import TYPE_CHECKING, Union
from typing import Tuple
from warnings import catch_warnings

import pytest

from litestar import MediaType, asgi, get
from litestar.datastructures.headers import MutableScopeHeaders
from litestar.exceptions import LitestarWarning, ValidationException
from litestar.middleware import AbstractMiddleware, ASGIMiddleware, DefineMiddleware
from litestar.response.base import ASGIResponse
from litestar.status_codes import HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Message, Receive, Scope, Send


def test_custom_middleware() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
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
        exclude = r"^/123"

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
                await send(message)

            await self.app(scope, receive, _send)

    @get("/123")
    def first_handler() -> dict:
        return {"hello": "world"}

    @get("/456")
    def second_handler() -> dict:
        return {"hello": "world"}

    @asgi("/mount", is_mount=True)
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=b"ok", media_type=MediaType.TEXT)
        await response(scope, receive, send)

    with create_test_client(
        [first_handler, second_handler, handler], middleware=[DefineMiddleware(SubclassMiddleware)]
    ) as client:
        response = client.get("/123")
        assert "test" not in response.headers

        response = client.get("/456")
        assert "test" in response.headers

        response = client.get("/mount/123")
        assert "test" in response.headers


def test_exclude_by_pattern_list() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        exclude = ["123", "456"]

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
                await send(message)

            await self.app(scope, receive, _send)

    @get("/123")
    def first_handler() -> dict:
        return {"hello": "world"}

    @get("/456")
    def second_handler() -> dict:
        return {"hello": "world"}

    @get("/789")
    def third_handler() -> dict:
        return {"hello": "world"}

    with create_test_client(
        [first_handler, second_handler, third_handler], middleware=[DefineMiddleware(SubclassMiddleware)]
    ) as client:
        response = client.get("/123")
        assert "test" not in response.headers
        response = client.get("/456")
        assert "test" not in response.headers
        response = client.get("/789")
        assert "test" in response.headers


@pytest.mark.parametrize("excludes", ["/", ["/", "/foo"], "/*", "/.*"])
def test_exclude_by_pattern_warns_if_exclude_all(excludes: Union[str, list[str]]) -> None:
    class SubclassMiddleware(AbstractMiddleware):
        exclude = excludes

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            await self.app(scope, receive, send)

    with pytest.warns(LitestarWarning, match="Middleware 'SubclassMiddleware' exclude pattern"):
        create_test_client(middleware=[SubclassMiddleware])


def test_exclude_doesnt_warn_on_non_greedy_pattern() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        exclude = "^/$"

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            await self.app(scope, receive, send)

    with catch_warnings(record=True) as warnings:
        create_test_client(middleware=[SubclassMiddleware])
        assert len(warnings) == 0


def test_exclude_by_opt_key() -> None:
    class SubclassMiddleware(AbstractMiddleware):
        exclude_opt_key = "exclude_route"

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
                await send(message)

                await self.app(scope, receive, _send)

    @get("/", exclude_route=True)
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[DefineMiddleware(SubclassMiddleware)]) as client:
        response = client.get("/")
        assert "test" not in response.headers


def test_abstract_middleware_deprecation_warning() -> None:
    with pytest.warns(DeprecationWarning, match="AbstractMiddleware"):

        class MyMiddleware(AbstractMiddleware):
            pass


def test_asgi_middleware() -> None:
    class SubclassMiddleware(ASGIMiddleware):
        async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
                await send(message)

            await next_app(scope, receive, _send)

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[SubclassMiddleware()]) as client:
        response = client.get("/")
        assert response.headers["test"] == "123"


def test_asgi_middleware_raises_exception() -> None:
    class SubclassMiddleware(ASGIMiddleware):
        async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
            raise ValidationException(detail="nope")

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[SubclassMiddleware()]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_asgi_middleware_exclude_by_pattern() -> None:
    class SubclassMiddleware(ASGIMiddleware):
        def __init__(self) -> None:
            self.exclude_path_pattern = r"^/123"

        async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
                await send(message)

            await next_app(scope, receive, _send)

    @get("/123")
    def first_handler() -> dict:
        return {"hello": "world"}

    @get("/456")
    def second_handler() -> dict:
        return {"hello": "world"}

    @asgi("/mount", is_mount=True)
    async def handler(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = ASGIResponse(body=b"ok", media_type=MediaType.TEXT)
        await response(scope, receive, send)

    with create_test_client([first_handler, second_handler, handler], middleware=[SubclassMiddleware()]) as client:
        response = client.get("/123")
        assert "test" not in response.headers

        response = client.get("/456")
        assert "test" in response.headers

        response = client.get("/mount/123")
        assert "test" in response.headers


def test_asgi_middleware_exclude_by_pattern_tuple() -> None:
    class SubclassMiddleware(ASGIMiddleware):
        exclude_path_pattern = ("123", "456")

        async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
                await send(message)

            await next_app(scope, receive, _send)

    @get("/123")
    def first_handler() -> dict:
        return {"hello": "world"}

    @get("/456")
    def second_handler() -> dict:
        return {"hello": "world"}

    @get("/789")
    def third_handler() -> dict:
        return {"hello": "world"}

    with create_test_client(
        [first_handler, second_handler, third_handler], middleware=[SubclassMiddleware()]
    ) as client:
        response = client.get("/123")
        assert "test" not in response.headers
        response = client.get("/456")
        assert "test" not in response.headers
        response = client.get("/789")
        assert "test" in response.headers


@pytest.mark.parametrize("excludes", ["/", ("/", "/foo"), "/*", "/.*"])
def test_asgi_middleware_exclude_by_pattern_warns_if_exclude_all(excludes: Union[str, Tuple[str, ...]]) -> None:
    class SubclassMiddleware(ASGIMiddleware):
        exclude_path_pattern = excludes

        async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
            await next_app(scope, receive, send)

    with pytest.warns(LitestarWarning, match="Middleware 'SubclassMiddleware' exclude pattern"):
        create_test_client(middleware=[SubclassMiddleware()])


def test_asgi_middleware_exclude_doesnt_warn_on_non_greedy_pattern() -> None:
    class SubclassMiddleware(ASGIMiddleware):
        exclude_path_pattern = "^/$"

        async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
            await next_app(scope, receive, send)

    with catch_warnings(record=True) as warnings:
        create_test_client(middleware=[SubclassMiddleware()])
        assert len(warnings) == 0


def test_asgi_middleware_exclude_by_opt_key() -> None:
    class SubclassMiddleware(ASGIMiddleware):
        exclude_opt_key = "exclude_route"

        async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
            async def _send(message: "Message") -> None:
                if message["type"] == "http.response.start":
                    headers = MutableScopeHeaders(message)
                    headers.add("test", str(123))
                await send(message)

                await next_app(scope, receive, send)

    @get("/", exclude_route=True)
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=[SubclassMiddleware()]) as client:
        response = client.get("/")
        assert "test" not in response.headers
