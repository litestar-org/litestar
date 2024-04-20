from typing import TYPE_CHECKING, AsyncIterator

import pytest

from litestar.testing import AsyncTestClient

from my_app.main import app

if TYPE_CHECKING:
    from litestar import Litestar


@pytest.fixture(scope="function")
async def test_client() -> AsyncIterator[AsyncTestClient[Litestar]]:
    async with AsyncTestClient(app=app) as client:
        yield client