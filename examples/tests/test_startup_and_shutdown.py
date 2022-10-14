from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

from examples import startup_and_shutdown
from starlite import State, get
from starlite.testing import TestClient

if TYPE_CHECKING:
    from pytest import MonkeyPatch  # noqa:PT013


class FakeAsyncEngine:
    dispose = AsyncMock()


async def test_startup_and_shutdown_example(monkeypatch: "MonkeyPatch") -> None:

    monkeypatch.setattr(startup_and_shutdown, "create_async_engine", MagicMock(return_value=FakeAsyncEngine))

    @get("/")
    def handler(state: State) -> None:
        assert state.engine is FakeAsyncEngine

    startup_and_shutdown.app.register(handler)

    with TestClient(app=startup_and_shutdown.app) as client:
        client.get("/")
    FakeAsyncEngine.dispose.assert_awaited_once()
