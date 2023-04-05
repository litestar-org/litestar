from litestar import Litestar, MediaType, Request, Response, get, post
from litestar.exceptions import InternalServerException, NotFoundException
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import TestClient, create_test_client
from tests import Person


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

    with create_test_client(my_route_handler, exception_handlers={NotFoundException: my_custom_handler}) as client:
        response = client.get("/abc")
        assert response.text == "custom message"
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_debug_response_created() -> None:
    # this will test exception causes are recorded in output
    # since frames include code in context we should not raise
    # exception directly
    def exception_thrower() -> float:
        return 1 / 0

    @get("/")
    def my_route_handler() -> None:
        try:
            exception_thrower()
        except Exception as e:
            raise InternalServerException() from e

    app = Litestar(route_handlers=[my_route_handler], debug=True)
    client = TestClient(app=app)

    response = client.get("/")
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert "text/plain" in response.headers["content-type"]

    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert "text/html" in response.headers["content-type"]
    assert "ZeroDivisionError" in response.text


def test_handler_error_return_status_500() -> None:
    @get("/")
    def my_route_handler() -> None:
        raise KeyError("custom message")

    with create_test_client(my_route_handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
