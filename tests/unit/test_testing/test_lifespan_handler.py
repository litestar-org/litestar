import pytest

from litestar.testing.life_span_handler import LifeSpanHandler
from litestar.types import Receive, Scope, Send

pytestmark = pytest.mark.filterwarnings("default")


async def test_wait_startup_invalid_event() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "lifespan.startup.something_unexpected"})  # type: ignore[typeddict-item]

    with pytest.RaisesGroup(pytest.RaisesExc(RuntimeError, match="Received unexpected ASGI message type")):
        async with LifeSpanHandler(app):
            pass


async def test_wait_shutdown_invalid_event() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "lifespan.startup.complete"})  # type: ignore[typeddict-item]
        await send({"type": "lifespan.shutdown.something_unexpected"})  # type: ignore[typeddict-item]

    with pytest.RaisesGroup(pytest.RaisesExc(RuntimeError, match="Received unexpected ASGI message type")):
        async with LifeSpanHandler(app):
            pass
