import json
from typing import TYPE_CHECKING, Any

from starlette.exceptions import HTTPException as StarletteHTTPException

from starlite import HTTPException, Request, Response, Starlite, get
from starlite.middleware.exceptions import ExceptionHandlerMiddleware
from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from starlite.datastructures import State
    from starlite.types import Scope


async def dummy_app(scope: Any, receive: Any, send: Any) -> None:
    return None


middleware = ExceptionHandlerMiddleware(dummy_app, False, {})


def test_default_handle_http_exception_handling_extra_object() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),  # type: ignore
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
        Request(scope={"type": "http", "method": "GET"}),  # type: ignore
        HTTPException(detail="starlite_exception"),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {"detail": "starlite_exception", "status_code": 500}


def test_default_handle_starlite_http_exception_handling() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),  # type: ignore
        HTTPException(detail="starlite_exception"),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {"detail": "starlite_exception", "status_code": 500}


def test_default_handle_starlite_http_exception_extra_list() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),  # type: ignore
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
        Request(scope={"type": "http", "method": "GET"}),  # type: ignore
        StarletteHTTPException(detail="starlite_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "status_code": 500,
    }


def test_default_handle_python_http_exception_handling() -> None:
    response = middleware.default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}), AttributeError("oops")  # type: ignore
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
        return Response(content={"an": "error"}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    app = Starlite(route_handlers=[handler], exception_handlers={Exception: exception_handler}, openapi_config=None)
    assert app.asgi_router.root_route_map_node["children"]["/"]["asgi_handlers"]["GET"][0].exception_handlers == {
        Exception: exception_handler
    }


def test_exception_handler_middleware_calls_app_level_after_exception_hook() -> None:
    @get("/test")
    def handler() -> None:
        raise RuntimeError()

    async def after_exception_hook_handler(exc: Exception, scope: "Scope", state: "State") -> None:
        assert isinstance(exc, RuntimeError)
        assert scope["app"]
        assert not state.called
        state.called = True

    with create_test_client(handler, after_exception=after_exception_hook_handler) as client:
        setattr(client.app.state, "called", False)  # noqa: B010
        assert not client.app.state.called
        response = client.get("/test")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert client.app.state.called
