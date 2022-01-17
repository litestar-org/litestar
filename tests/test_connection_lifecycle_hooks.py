import pytest

from starlite import Request, Response, create_test_client, get


def greet() -> dict:
    return {"hello": "world"}


def sync_before_request_handler_with_return_value(request: Request) -> dict:
    assert isinstance(request, Request)
    return {"hello": "moon"}


async def async_before_request_handler_with_return_value(request: Request) -> dict:
    assert isinstance(request, Request)
    return {"hello": "moon"}


def sync_before_request_handler_without_return_value(request: Request) -> None:
    assert isinstance(request, Request)
    return None


async def async_before_request_handler_without_return_value(request: Request) -> None:
    assert isinstance(request, Request)
    return None


@pytest.mark.parametrize(
    "handler, expected",
    [
        [get(path="/")(greet), {"hello": "world"}],
        [get(path="/", before_request=sync_before_request_handler_with_return_value)(greet), {"hello": "moon"}],
        [get(path="/", before_request=async_before_request_handler_with_return_value)(greet), {"hello": "moon"}],
        [get(path="/", before_request=sync_before_request_handler_without_return_value)(greet), {"hello": "world"}],
        [get(path="/", before_request=async_before_request_handler_without_return_value)(greet), {"hello": "world"}],
    ],
)
def test_before_request_handler_called(handler, expected):
    with create_test_client(route_handlers=handler) as client:
        response = client.get("/")
        assert response.json() == expected


def sync_after_request_handler(response: Response) -> Response:
    assert isinstance(response, Response)
    response.body = response.render({"hello": "moon"})
    return response


async def async_after_request_handler(response: Response) -> Response:
    assert isinstance(response, Response)
    response.body = response.render({"hello": "moon"})
    return response


@pytest.mark.parametrize(
    "handler, expected",
    [
        [get(path="/")(greet), {"hello": "world"}],
        [get(path="/", after_request=sync_after_request_handler)(greet), {"hello": "moon"}],
        [get(path="/", after_request=async_after_request_handler)(greet), {"hello": "moon"}],
    ],
)
def test_after_request_handler_called(handler, expected):
    with create_test_client(route_handlers=handler) as client:
        response = client.get("/")
        assert response.json() == expected
