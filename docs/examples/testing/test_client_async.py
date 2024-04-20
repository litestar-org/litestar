from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from my_app.main import app


async def test_health_check():
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"