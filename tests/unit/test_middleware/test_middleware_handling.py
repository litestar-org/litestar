import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List

from _pytest.capture import CaptureFixture
from _pytest.logging import LogCaptureFixture

from litestar import Controller, Request, Router, get, post
from litestar.enums import ScopeType
from litestar.middleware import MiddlewareProtocol
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from typing import Type

    from litestar.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class MiddlewareProtocolRequestLoggingMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", kwarg: str = "") -> None:
        self.app = app
        self.kwarg = kwarg

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] == ScopeType.HTTP:
            request = Request[Any, Any, Any](scope=scope, receive=receive)
            body = await request.json()
            logger.info(f"test logging: {request.method}, {request.url}, {body}")
        await self.app(scope, receive, send)


def test_request_body_logging_middleware(caplog: LogCaptureFixture, capsys: "CaptureFixture[str]") -> None:
    @dataclass
    class JSONRequest:
        name: str
        age: int
        programmer: bool

    @post(path="/")
    def post_handler(data: JSONRequest) -> JSONRequest:
        return data

    if sys.version_info < (3, 13):
        with caplog.at_level(logging.INFO):
            client = create_test_client(
                route_handlers=[post_handler], middleware=[MiddlewareProtocolRequestLoggingMiddleware]
            )
            response = client.post("/", json={"name": "moishe zuchmir", "age": 40, "programmer": True})
            assert response.status_code == 201
            assert "test logging" in caplog.text
    else:
        client = create_test_client(
            route_handlers=[post_handler], middleware=[MiddlewareProtocolRequestLoggingMiddleware]
        )
        response = client.post("/", json={"name": "moishe zuchmir", "age": 40, "programmer": True})
        assert response.status_code == 201
        log = capsys.readouterr()
        assert "test logging" in log.err


def test_middleware_call_order() -> None:
    """Test that middlewares are called in the order they have been passed."""

    results: List[int] = []

    def create_test_middleware(middleware_id: int) -> "Type[MiddlewareProtocol]":
        class TestMiddleware(MiddlewareProtocol):
            def __init__(self, app: "ASGIApp") -> None:
                self.app = app

            async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
                results.append(middleware_id)
                await self.app(scope, receive, send)

        return TestMiddleware

    class MyController(Controller):
        path = "/controller"
        middleware = [create_test_middleware(4), create_test_middleware(5)]

        @get("/handler", middleware=[create_test_middleware(6), create_test_middleware(7)])
        def my_handler(self) -> None:
            return None

    router = Router(
        path="/router", route_handlers=[MyController], middleware=[create_test_middleware(2), create_test_middleware(3)]
    )

    with create_test_client(
        route_handlers=[router],
        middleware=[create_test_middleware(0), create_test_middleware(1)],
    ) as client:
        client.get("/router/controller/handler")

        assert results == [0, 1, 2, 3, 4, 5, 6, 7]
