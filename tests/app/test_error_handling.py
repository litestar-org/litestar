import json

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from starlite import (
    HTTPException,
    MediaType,
    Request,
    Response,
    Starlite,
    TestClient,
    create_test_client,
    get,
    post,
)
from starlite.exceptions import InternalServerException
from tests import Person


def test_default_handle_http_exception_handling() -> None:
    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra={"key": "value"}),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": {"key": "value"},
        "status_code": 500,
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception"),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": None,
        "status_code": 500,
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra=None),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": None,
        "status_code": 500,
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        HTTPException(detail="starlite_exception", extra=["extra-1", "extra-2"]),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
        "extra": ["extra-1", "extra-2"],
        "status_code": 500,
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}),
        StarletteHTTPException(detail="starlite_exception", status_code=HTTP_500_INTERNAL_SERVER_ERROR),
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": "starlite_exception",
    }

    response = Starlite(route_handlers=[]).default_http_exception_handler(
        Request(scope={"type": "http", "method": "GET"}), AttributeError("oops")
    )
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert json.loads(response.body) == {
        "detail": repr(AttributeError("oops")),
    }


def test_default_handling_of_pydantic_errors() -> None:
    @post("/{param:int}")
    def my_route_handler(param: int, data: Person) -> None:
        ...

    with create_test_client(my_route_handler) as client:
        response = client.post("/123", json={"first_name": "moishe"})
        extra = response.json().get("extra")
        assert extra is not None
        assert len(extra) == 3


def test_using_custom_http_exception_handler() -> None:
    @get("/{param:int}")
    def my_route_handler(param: int) -> None:
        ...

    def my_custom_handler(_: Request, __: Exception) -> Response:
        return Response(content="custom message", media_type=MediaType.TEXT, status_code=HTTP_400_BAD_REQUEST)

    with create_test_client(my_route_handler, exception_handlers={HTTP_400_BAD_REQUEST: my_custom_handler}) as client:
        response = client.get("/abc")
        assert response.text == "custom message"
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_uses_starlette_debug_responses() -> None:
    @get("/")
    def my_route_handler() -> None:
        raise InternalServerException()

    app = Starlite(route_handlers=[my_route_handler], debug=True)
    client = TestClient(app=app)

    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert "text/html" in response.headers["content-type"]


def test_handler_error_return_status_500() -> None:
    @get("/")
    def my_route_handler() -> None:
        raise KeyError("custom message")

    with create_test_client(my_route_handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
