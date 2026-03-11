from collections.abc import Generator
from inspect import getinnerframes
from typing import TYPE_CHECKING, Any, Callable
from unittest.mock import MagicMock

import pydantic
import pytest
from pytest_mock import MockerFixture
from starlette.exceptions import HTTPException as StarletteHTTPException

from litestar import Litestar, MediaType, Request, Response, WebSocket, get, websocket
from litestar.exceptions import HTTPException, InternalServerException, LitestarException, ValidationException
from litestar.exceptions.responses._debug_response import get_symbol_name
from litestar.middleware._internal.exceptions.middleware import (
    ExceptionHandlerMiddleware,
    _starlette_exception_handler,
    get_exception_handler,
)
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import TestClient, create_test_client
from litestar.types import ExceptionHandlersMap
from litestar.types.asgi_types import HTTPReceiveMessage, HTTPScope, Message, Receive, Scope, Send
from litestar.utils.scope.state import ScopeState
from tests.helpers import cleanup_logging_impl

if TYPE_CHECKING:
    from litestar.types import Scope


async def dummy_app(scope: Any, receive: Any, send: Any) -> None:
    return None


@pytest.fixture(autouse=True)
def cleanup_logging() -> Generator:
    with cleanup_logging_impl():
        yield


@pytest.fixture()
def app() -> Litestar:
    return Litestar()


@pytest.fixture()
def middleware() -> ExceptionHandlerMiddleware:
    return ExceptionHandlerMiddleware(dummy_app)


@pytest.fixture()
def scope(create_scope: Callable[..., HTTPScope], app: Litestar) -> HTTPScope:
    return create_scope(app=app)


def test_default_handle_http_exception_handling_extra_object(
    scope: HTTPScope, middleware: ExceptionHandlerMiddleware
) -> None:
    @get("/")
    async def handler() -> None:
        raise HTTPException(detail="litestar_exception", extra={"key": "value"})

    with create_test_client([handler]) as client:
        response = client.get("/")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "Internal Server Error",
        "extra": {"key": "value"},
        "status_code": 500,
    }


def test_default_handle_http_exception_handling_extra_none(
    scope: HTTPScope, middleware: ExceptionHandlerMiddleware
) -> None:
    @get("/")
    async def handler() -> None:
        raise HTTPException(detail="litestar_exception")

    with create_test_client([handler]) as client:
        response = client.get("/")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Internal Server Error", "status_code": 500}


def test_default_handle_litestar_http_exception_handling(
    scope: HTTPScope, middleware: ExceptionHandlerMiddleware
) -> None:
    @get("/")
    async def handler() -> None:
        raise HTTPException(detail="litestar_exception")

    with create_test_client([handler]) as client:
        response = client.get("/")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Internal Server Error", "status_code": 500}


def test_default_handle_litestar_http_exception_extra_list(
    scope: HTTPScope, middleware: ExceptionHandlerMiddleware
) -> None:
    @get("/")
    async def handler() -> None:
        raise HTTPException(detail="litestar_exception", extra=["extra-1", "extra-2"])

    with create_test_client([handler]) as client:
        response = client.get("/")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "Internal Server Error",
        "extra": ["extra-1", "extra-2"],
        "status_code": 500,
    }


def test_default_handle_starlette_http_exception_handling(
    scope: HTTPScope, middleware: ExceptionHandlerMiddleware
) -> None:
    @get("/")
    async def handler() -> None:
        raise StarletteHTTPException(detail="litestar_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    with create_test_client([handler]) as client:
        response = client.get("/")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Internal Server Error", "status_code": 500}


def test_unhandled_exception(scope: HTTPScope, middleware: ExceptionHandlerMiddleware) -> None:
    # an exception without a dedicated handler should not be handled
    @get("/")
    async def handler() -> None:
        raise AttributeError("oops")

    with pytest.raises(AttributeError, match="oops"):
        with create_test_client([handler], raise_server_exceptions=True) as client:
            client.get("/")


def test_exception_handler_middleware_exception_handlers_mapping() -> None:
    mock = MagicMock()

    @get("/")
    def handler(request: Request) -> None:
        mock(ScopeState.from_scope(request.scope).exception_handlers)

    def exception_handler(request: Request, exc: Exception) -> Response:
        return Response(content={"an": "error"}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    app = Litestar(route_handlers=[handler], exception_handlers={Exception: exception_handler}, openapi_config=None)

    with TestClient(app) as client:
        client.get("/")
        mock.assert_called_once()
        assert mock.call_args[0][0] == {
            Exception: exception_handler,
            StarletteHTTPException: _starlette_exception_handler,
        }


def test_exception_handler_middleware_handler_response_type_encoding(
    scope: HTTPScope, middleware: ExceptionHandlerMiddleware
) -> None:
    class ErrorMessage(pydantic.BaseModel):
        message: str

    @get("/")
    def handler(_: Request) -> None:
        raise Exception

    def exception_handler(_: Request, _e: Exception) -> Response:
        return Response(content=ErrorMessage(message="the error message"), status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    app = Litestar(route_handlers=[handler], exception_handlers={Exception: exception_handler}, openapi_config=None)

    with TestClient(app) as client:
        response = client.get("/")
        assert response.json() == {"message": "the error message"}


def test_exception_handler_middleware_handler_response_type_encoding_no_route_handler(
    scope: HTTPScope, middleware: ExceptionHandlerMiddleware
) -> None:
    class ErrorMessage(pydantic.BaseModel):
        message: str

    @get("/")
    def handler(_: Request) -> None:
        raise Exception

    def exception_handler(_: Request, _e: Exception) -> Response:
        return Response(content=ErrorMessage(message="the error message"), status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    app = Litestar(route_handlers=[handler], exception_handlers={Exception: exception_handler}, openapi_config=None)

    with TestClient(app) as client:
        response = client.get("/not-found")
        assert response.json() == {"message": "the error message"}


def test_exception_handler_middleware_calls_app_level_after_exception_hook() -> None:
    @get("/test")
    def handler() -> None:
        raise RuntimeError()

    async def after_exception_hook_handler(exc: Exception, scope: "Scope") -> None:
        app = scope.get("app")
        assert isinstance(exc, RuntimeError)
        assert app
        assert not app.state.called
        app.state.called = True

    with create_test_client(handler, after_exception=[after_exception_hook_handler]) as client:
        setattr(client.app.state, "called", False)
        assert not client.app.state.called
        response = client.get("/test")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert client.app.state.called


def handler(_: Any, __: Any) -> Any:
    return None


def handler_2(_: Any, __: Any) -> Any:
    return None


@pytest.mark.parametrize(
    ["mapping", "exc", "expected"],
    [
        ({}, Exception, None),
        ({HTTP_400_BAD_REQUEST: handler}, ValidationException(), handler),
        ({InternalServerException: handler}, InternalServerException(), handler),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler}, Exception(), handler),
        ({TypeError: handler}, TypeError(), handler),
        ({Exception: handler}, ValidationException(), handler),
        ({ValueError: handler}, ValidationException(), handler),
        ({ValidationException: handler}, Exception(), None),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler}, ValidationException(), None),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler, HTTPException: handler_2}, ValidationException(), handler_2),
        ({HTTPException: handler, ValidationException: handler_2}, ValidationException(), handler_2),
        ({HTTPException: handler, ValidationException: handler_2}, InternalServerException(), handler),
        ({HTTP_500_INTERNAL_SERVER_ERROR: handler, HTTPException: handler_2}, InternalServerException(), handler),
    ],
)
def test_get_exception_handler(mapping: ExceptionHandlersMap, exc: Exception, expected: Any) -> None:
    assert get_exception_handler(mapping, exc) == expected


@pytest.mark.filterwarnings("ignore::litestar.utils.warnings.LitestarWarning:")
def test_pdb_on_exception(mocker: MockerFixture) -> None:
    @get("/test")
    def handler() -> None:
        raise ValueError("Test debug exception")

    mock_post_mortem = mocker.patch("litestar.app.pdb.post_mortem")

    app = Litestar([handler], pdb_on_exception=True)

    with TestClient(app=app) as client:
        response = client.get("/test")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    mock_post_mortem.assert_called_once()


def test_get_debug_from_scope() -> None:
    @get("/test")
    def handler() -> None:
        raise ValueError("Test debug exception")

    app = Litestar([handler], debug=True)

    with TestClient(app=app) as client:
        response = client.get("/test")

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "Test debug exception" in response.text


def test_get_symbol_name_where_type_doesnt_support_bool() -> None:
    class Test:
        def __bool__(self) -> bool:
            raise TypeError("This type doesn't support bool")

        def method(self) -> None:
            raise RuntimeError("Oh no!")

    exc = None

    try:
        Test().method()
    except Exception as e:
        exc = e

    if exc is not None and exc.__traceback__ is not None:
        frame = getinnerframes(exc.__traceback__, 2)[-1]
        assert get_symbol_name(frame) == "Test.method"


@pytest.mark.parametrize("media_type", list(MediaType))
def test_serialize_custom_types(media_type: MediaType) -> None:
    # ensure type encoders are passed down to the created response so custom types that
    # might end up as part of a ValidationException are handled properly
    # https://github.com/litestar-org/litestar/issues/2867
    # https://github.com/litestar-org/litestar/issues/3192
    class Foo:
        def __init__(self, value: str) -> None:
            self.value = value

    @get(media_type=media_type)
    def handler() -> None:
        raise ValidationException(extra={"foo": Foo("bar")})

    with create_test_client([handler], type_encoders={Foo: lambda f: f.value}) as client:
        res = client.get("/")
        assert res.json()["extra"] == {"foo": "bar"}


async def test_exception_handler_middleware_response_already_started(scope: HTTPScope) -> None:
    assert not ScopeState.from_scope(scope).response_started

    async def mock_receive() -> HTTPReceiveMessage:  # type: ignore[empty-body]
        pass

    mock = MagicMock()

    async def mock_send(message: Message) -> None:
        mock(message)

    start_message: Message = {"type": "http.response.start", "status": 200, "headers": []}

    async def asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(start_message)
        raise RuntimeError("Test exception")

    mw = ExceptionHandlerMiddleware(asgi_app)

    with pytest.raises(LitestarException):
        await mw(scope, mock_receive, mock_send)

    mock.assert_called_once_with(start_message)
    assert ScopeState.from_scope(scope).response_started


@pytest.mark.parametrize("accept", [True, False])
def test_unhandled_exception_in_websocket_reraised(accept: bool) -> None:
    @websocket("/")
    async def handler(socket: WebSocket) -> None:
        if accept:
            await socket.accept()
        raise ValueError("foo")

    with pytest.raises(ValueError, match="foo"):
        with create_test_client([handler]) as client, client.websocket_connect("/"):
            pass
