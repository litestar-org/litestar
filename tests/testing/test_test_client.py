from typing import TYPE_CHECKING, Any, NoReturn

import pytest

from starlite import Starlite, get
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient

if TYPE_CHECKING:
    from starlite.types import (
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        Receive,
        Scope,
        Send,
    )


def test_use_testclient_in_endpoint() -> None:
    """this test is taken from starlette."""

    @get("/")
    def mock_service_endpoint() -> dict:
        return {"mock": "example"}

    mock_service = Starlite(route_handlers=[mock_service_endpoint])

    @get("/")
    def homepage() -> Any:
        client = TestClient(mock_service)
        response = client.get("/")
        return response.json()

    app = Starlite(route_handlers=[homepage])

    client = TestClient(app)
    response = client.get("/")
    assert response.json() == {"mock": "example"}


def raise_error() -> NoReturn:
    raise RuntimeError()


def test_error_handling_on_startup() -> None:
    with pytest.raises(RuntimeError), TestClient(Starlite(route_handlers=[], on_startup=[raise_error])):
        pass


def test_error_handling_on_shutdown() -> None:
    with pytest.raises(RuntimeError), TestClient(Starlite(route_handlers=[], on_shutdown=[raise_error])):
        pass


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head", "options"])
def test_client_interface(method: str) -> None:
    async def asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        start_event: "HTTPResponseStartEvent" = {
            "type": "http.response.start",
            "status": HTTP_200_OK,
            "headers": [(b"content-type", b"text/plain")],
        }
        await send(start_event)
        body_event: "HTTPResponseBodyEvent" = {"type": "http.response.body", "body": b"", "more_body": False}
        await send(body_event)

    client = TestClient(asgi_app)
    if method == "get":
        response = client.get("/")
    elif method == "post":
        response = client.post("/")
    elif method == "put":
        response = client.put("/")
    elif method == "patch":
        response = client.patch("/")
    elif method == "delete":
        response = client.delete("/")
    elif method == "head":
        response = client.head("/")
    else:
        response = client.options("/")
    assert response.status_code == HTTP_200_OK
