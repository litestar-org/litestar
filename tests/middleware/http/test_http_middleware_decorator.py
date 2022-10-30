from typing import TYPE_CHECKING, Any

from starlite import create_test_client, get, http_middleware

if TYPE_CHECKING:
    from starlite import CallNext, Request, Response


def test_http_middleware_decorator_decorates() -> None:
    @get("/")
    def handler() -> None:
        return

    @http_middleware()
    async def my_middleware(request: "Request[Any, Any]", call_next: "CallNext") -> "Response[Any]":
        response = await call_next(request)
        response.set_header("X-My-Header", "123")
        return response

    with create_test_client(handler, middleware=[my_middleware]) as client:
        response = client.get("/")
        assert response.headers["X-My-Header"] == "123"


def test_middleware_exclusion_by_pattern() -> None:
    @get("/first")
    def first_handler() -> None:
        return

    @get("/second")
    def second_handler() -> None:
        return

    @http_middleware(exclude="second")
    async def my_middleware(request: "Request[Any, Any]", call_next: "CallNext") -> "Response[Any]":
        response = await call_next(request)
        response.set_header("X-My-Header", "123")
        return response

    with create_test_client([first_handler, second_handler], middleware=[my_middleware]) as client:
        response = client.get("/first")
        assert response.headers["X-My-Header"] == "123"

        response = client.get("/second")
        assert response.headers.get("X-My-Header") is None


def test_middleware_exclusion_by_opt_key() -> None:
    @get("/first")
    def first_handler() -> None:
        return

    @get("/second", exclude_this_path=True)
    def second_handler() -> None:
        return

    @http_middleware(exclude_opt_key="exclude_this_path")
    async def my_middleware(request: "Request[Any, Any]", call_next: "CallNext") -> "Response[Any]":
        response = await call_next(request)
        response.set_header("X-My-Header", "123")
        return response

    with create_test_client([first_handler, second_handler], middleware=[my_middleware]) as client:
        response = client.get("/first")
        assert response.headers["X-My-Header"] == "123"

        response = client.get("/second")
        assert response.headers.get("X-My-Header") is None
