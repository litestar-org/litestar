from typing import TYPE_CHECKING, Any

import pytest

from starlite import HttpMethod, Starlite, get
from starlite.testing import AsyncTestClient

if TYPE_CHECKING:
    from starlite.types import AnyIOBackend

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
