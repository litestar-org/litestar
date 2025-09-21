import asyncio

import pytest_asyncio

from litestar import get, Litestar
from litestar.testing import AsyncTestClient, TestClient


@get("/")
async def handler() -> dict[str, int]:
    return {"loop_id": id(asyncio.get_running_loop())}


@pytest_asyncio.fixture()
async def fixture_loop_id() -> int:
    return id(asyncio.get_running_loop())


def test_handler(fixture_loop_id: int) -> None:
    app = Litestar([handler])

    with TestClient(app) as client:
        response = client.get("/")
        assert response.json() == {"loop_id": fixture_loop_id}


async def test_handler_async(fixture_loop_id: int) -> None:
    app = Litestar([handler])

    async with AsyncTestClient(app) as client:
        response = await client.get("/")
        assert response.json() == {"loop_id": fixture_loop_id}
