from typing import TYPE_CHECKING, List

from litestar.datastructures import State
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar import Litestar


def test_lifespan() -> None:
    events: List[str] = []
    counter = {"value": 0}

    async def before_startup(app: "Litestar") -> None:
        events.append("before_startup")
        assert app

    async def after_startup(app: "Litestar") -> None:
        events.append("after_startup")
        assert app

    async def before_shutdown(app: "Litestar") -> None:
        events.append("before_shutdown")
        assert app

    async def after_shutdown(app: "Litestar") -> None:
        events.append("after_shutdown")
        assert app

    def sync_function_without_state() -> None:
        events.append("sync_function_without_state")
        counter["value"] += 1

    async def async_function_without_state() -> None:
        events.append("async_function_without_state")
        counter["value"] += 1

    def sync_function_with_state(state: "State") -> None:
        events.append("sync_function_with_state")
        assert state is not None
        assert isinstance(state, State)
        counter["value"] += 1
        state.x = True

    async def async_function_with_state(state: "State") -> None:
        events.append("async_function_with_state")
        assert state is not None
        assert isinstance(state, State)
        counter["value"] += 1
        state.y = True

    with create_test_client(
        [],
        after_shutdown=[after_shutdown],
        after_startup=[after_startup],
        before_shutdown=[before_shutdown],
        before_startup=[before_startup],
        on_startup=[
            sync_function_without_state,
            async_function_without_state,
            sync_function_with_state,
            async_function_with_state,
        ],
        on_shutdown=[
            sync_function_without_state,
            async_function_without_state,
            sync_function_with_state,
            async_function_with_state,
        ],
    ) as client:
        assert counter["value"] == 4
        assert client.app.state.x
        assert client.app.state.y
        counter["value"] = 0
        assert counter["value"] == 0
    assert counter["value"] == 4
    assert events == [
        "before_startup",
        "sync_function_without_state",
        "async_function_without_state",
        "sync_function_with_state",
        "async_function_with_state",
        "after_startup",
        "before_shutdown",
        "sync_function_without_state",
        "async_function_without_state",
        "sync_function_with_state",
        "async_function_with_state",
        "after_shutdown",
    ]
