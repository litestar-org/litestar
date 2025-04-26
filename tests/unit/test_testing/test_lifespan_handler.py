import asyncio
import contextlib
from asyncio import get_event_loop
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest

from litestar import Litestar, get
from litestar.testing import AsyncTestClient, TestClient
from litestar.testing.life_span_handler import LifeSpanHandler
from litestar.types import Receive, Scope, Send

pytestmark = pytest.mark.filterwarnings("default")


async def test_wait_startup_invalid_event() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "lifespan.startup.something_unexpected"})  # type: ignore[typeddict-item]

    with pytest.raises(RuntimeError, match="Received unexpected ASGI message type"):
        with LifeSpanHandler(TestClient(app)):
            pass


async def test_wait_shutdown_invalid_event() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "lifespan.startup.complete"})  # type: ignore[typeddict-item]
        await send({"type": "lifespan.shutdown.something_unexpected"})  # type: ignore[typeddict-item]

    with LifeSpanHandler(TestClient(app)) as handler:
        with pytest.raises(RuntimeError, match="Received unexpected ASGI message type"):
            await handler.wait_shutdown()


async def test_implicit_startup() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "lifespan.startup.complete"})  # type: ignore[typeddict-item]
        await send({"type": "lifespan.shutdown.complete"})  # type: ignore[typeddict-item]

    with pytest.warns(DeprecationWarning):
        handler = LifeSpanHandler(TestClient(app))
        await handler.wait_shutdown()
        handler.close()


async def test_multiple_clients_event_loop() -> None:
    @get("/")
    def return_loop_id() -> dict:
        return {"loop_id": id(get_event_loop())}

    app = Litestar(route_handlers=[return_loop_id])

    async with AsyncTestClient(app) as client_1, AsyncTestClient(app) as client_2:
        response_1 = await client_1.get("/")
        response_2 = await client_2.get("/")

    assert response_1.json() == response_2.json()


async def test_lifespan_loop() -> None:
    mock = MagicMock()

    @contextlib.asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
        mock(asyncio.get_running_loop())
        yield

    app = Litestar(lifespan=[lifespan])

    async with AsyncTestClient(app):
        pass

    mock.assert_called_once_with(asyncio.get_running_loop())
