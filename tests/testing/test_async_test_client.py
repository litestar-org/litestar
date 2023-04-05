from typing import TYPE_CHECKING, Any

import pytest

from starlite import Controller, Starlite, delete, get, head, patch, post, put
from starlite.enums import HttpMethod
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from starlite.testing import AsyncTestClient

if TYPE_CHECKING:
    from starlite.types import (
        AnyIOBackend,
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        Receive,
        Scope,
        Send,
    )

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_use_testclient_in_endpoint(test_client_backend: "AnyIOBackend") -> None:
    """this test is taken from starlette."""

    @get("/")
    async def mock_service_endpoint() -> dict:
        return {"mock": "example"}

    mock_service = Starlite(route_handlers=[mock_service_endpoint])

    @get("/")
    async def homepage() -> Any:
        client = AsyncTestClient(mock_service, backend=test_client_backend)
        response = await client.request("GET", "/")
        return response.json()

    app = Starlite(route_handlers=[homepage])

    client = AsyncTestClient(app)
    response = await client.request(HttpMethod.GET, "/")
    assert response.json() == {"mock": "example"}


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


def test_warns_problematic_domain() -> None:
    with pytest.warns(UserWarning):
        AsyncTestClient(app=mock_asgi_app, base_url="http://testserver")


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head", "options"])
async def test_client_interface(method: str, test_client_backend: "AnyIOBackend") -> None:
    async def asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        start_event: "HTTPResponseStartEvent" = {
            "type": "http.response.start",
            "status": HTTP_200_OK,
            "headers": [(b"content-type", b"text/plain")],
        }
        await send(start_event)
        body_event: "HTTPResponseBodyEvent" = {"type": "http.response.body", "body": b"", "more_body": False}
        await send(body_event)

    client = AsyncTestClient(asgi_app, backend=test_client_backend)
    if method == "get":
        response = await client.get("/")
    elif method == "post":
        response = await client.post("/")
    elif method == "put":
        response = await client.put("/")
    elif method == "patch":
        response = await client.patch("/")
    elif method == "delete":
        response = await client.delete("/")
    elif method == "head":
        response = await client.head("/")
    else:
        response = await client.options("/")
    assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head", "options"])
async def test_client_interface_context_manager(method: str, test_client_backend: "AnyIOBackend") -> None:
    class MockController(Controller):
        @get("/")
        def mock_service_endpoint_get(self) -> dict:
            return {"mock": "example"}

        @post("/")
        def mock_service_endpoint_post(self) -> dict:
            return {"mock": "example"}

        @put("/")
        def mock_service_endpoint_put(self) -> None:
            ...

        @patch("/")
        def mock_service_endpoint_patch(self) -> None:
            ...

        @delete("/")
        def mock_service_endpoint_delete(self) -> None:
            ...

        @head("/")
        def mock_service_endpoint_head(self) -> None:
            ...

    mock_service = Starlite(route_handlers=[MockController])
    async with AsyncTestClient(mock_service, backend=test_client_backend) as client:
        if method == "get":
            response = await client.get("/")
            assert response.status_code == HTTP_200_OK
        elif method == "post":
            response = await client.post("/")
            assert response.status_code == HTTP_201_CREATED
        elif method == "put":
            response = await client.put("/")
            assert response.status_code == HTTP_200_OK
        elif method == "patch":
            response = await client.patch("/")
            assert response.status_code == HTTP_200_OK
        elif method == "delete":
            response = await client.delete("/")
            assert response.status_code == HTTP_204_NO_CONTENT
        elif method == "head":
            response = await client.head("/")
            assert response.status_code == HTTP_200_OK
        else:
            response = await client.options("/")
            assert response.status_code == HTTP_204_NO_CONTENT
