from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.datastructures import State
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar import Litestar


def test_lifespan() -> None:
    events: list[str] = []
    counter = {"value": 0}

    def sync_function_without_app() -> None:
        events.append("sync_function_without_app")
        counter["value"] += 1

    async def async_function_without_app() -> None:
        events.append("async_function_without_app")
        counter["value"] += 1

    def sync_function_with_app(app: Litestar) -> None:
        events.append("sync_function_with_app")
        assert app is not None
        assert isinstance(app.state, State)
        counter["value"] += 1
        app.state.x = True

    async def async_function_with_app(app: Litestar) -> None:
        events.append("async_function_with_app")
        assert app is not None
        assert isinstance(app.state, State)
        counter["value"] += 1
        app.state.y = True

    with create_test_client(
        [],
        on_startup=[
            sync_function_without_app,
            async_function_without_app,
            sync_function_with_app,
            async_function_with_app,
        ],
        on_shutdown=[
            sync_function_without_app,
            async_function_without_app,
            sync_function_with_app,
            async_function_with_app,
        ],
    ) as client:
        assert counter["value"] == 4
        assert client.app.state.x
        assert client.app.state.y
        counter["value"] = 0
        assert counter["value"] == 0
    assert counter["value"] == 4
    assert events == [
        "sync_function_without_app",
        "async_function_without_app",
        "sync_function_with_app",
        "async_function_with_app",
        "sync_function_without_app",
        "async_function_without_app",
        "sync_function_with_app",
        "async_function_with_app",
    ]
