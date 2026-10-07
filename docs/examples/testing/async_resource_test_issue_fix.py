from collections.abc import AsyncIterator

import httpx2
import pytest
import pytest_asyncio

from litestar import Litestar, get
from litestar.testing import AsyncTestClient


@get("/")
async def handler(http_client: httpx2.AsyncClient) -> dict[str, int]:
    response = await http_client.get("https://example.org")
    return {"status": response.status_code}


def create_app(http_client: httpx2.AsyncClient) -> Litestar:
    async def provide_http_client() -> httpx2.AsyncClient:
        return http_client

    return Litestar([handler], dependencies={"http_client": provide_http_client})


@pytest_asyncio.fixture()
async def http_test_client() -> AsyncIterator[httpx2.AsyncClient]:
    client = httpx2.AsyncClient(headers={"Authorization": "something"})
    yield client
    await client.aclose()


@pytest.fixture()
def app(http_test_client: httpx2.AsyncClient) -> Litestar:
    return create_app(http_client=http_test_client)


async def test_handler(app: Litestar) -> None:
    async with AsyncTestClient(app) as client:
        response = await client.get("/")
        assert response.json() == {"status": 200}
