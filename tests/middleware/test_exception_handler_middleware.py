import json
from typing import TYPE_CHECKING, Any

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite import HTTPException, Request, Response, Starlite, get
from starlite.enums import MediaType
from starlite.middleware.exceptions import ExceptionHandlerMiddleware
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from starlite.datastructures import State
    from starlite.types import Scope


async def dummy_app(scope: Any, receive: Any, send: Any) -> None:
    return None


middleware = ExceptionHandlerMiddleware(dummy_app, False, {})


def test_default_handle_http_exception_handling_extra_object() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra={"key": "value"}),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": {"key": "value"},
        "status_code": 500,
    }


def test_default_handle_http_exception_handling_extra_none() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception"),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {"detail": "starlite_exception", "status_code": 500}


def test_default_handle_starlite_http_exception_handling() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception"),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {"detail": "starlite_exception", "status_code": 500}


def test_default_handle_starlite_http_exception_extra_list() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra=["extra-1", "extra-2"]),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": ["extra-1", "extra-2"],
        "status_code": 500,
    }


def test_default_handle_starlette_http_exception_handling() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        StarletteHTTPException(detail="starlite_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "status_code": 500,
    }


def test_default_handle_python_http_exception_handling() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}), AttributeError("oops")
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": repr(AttributeError("oops")),
        "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
    }


def test_exception_handler_middleware_exception_handlers_mapping() -> None:
    @get("/")
    def handler() -> None:
        ...

    def exception_handler(request: Request, exc: Exception) -> Response:
        return Response(content={"an": "error"}, status_code=HTTP_500_INTERNAL_SERVER_ERROR, media_type=MediaType.JSON)

    app = Starlite(route_handlers=[handler], exception_handlers={Exception: exception_handler}, openapi_config=None)
    assert app.route_map["/"]["_asgi_handlers"]["GET"].exception_handlers == {Exception: exception_handler}


def test_exception_handler_middleware_calls_app_level_after_exception_hook() -> None:
    @get("/test")
    def bla_handler() -> None:
        raise RuntimeError()

    async def after_exception_hook_handler(exc: Exception, scope: "Scope", state: "State") -> None:
        assert isinstance(exc, RuntimeError)
        assert scope["app"]
        assert not state.called
        state.called = True

    with create_test_client(bla_handler, after_exception=after_exception_hook_handler) as client:
        setattr(client.app.state, "called", False)  # noqa: B010
        assert not client.app.state.called
        response = client.get("/test")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert client.app.state.called
