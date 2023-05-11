import pytest

from litestar import Litestar, MediaType, get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient


@get(path="/health-check", media_type=MediaType.TEXT, sync_to_thread=False)
def health_check() -> str:
    return "healthy"


app = Litestar(route_handlers=[health_check])


async def test_health_check() -> None:
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"


@pytest.fixture(scope="function")
def test_client() -> AsyncTestClient:
    return AsyncTestClient(app=app)


async def test_health_check_with_fixture(test_client: AsyncTestClient) -> None:
    async with test_client as client:
        response = await client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
