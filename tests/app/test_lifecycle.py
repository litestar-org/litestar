from typing import cast

from starlite import Starlite, State
from starlite.testing import create_test_client


def test_lifecycle() -> None:
    counter = {"value": 0}

    def sync_function_without_state() -> None:
        counter["value"] += 1

    async def async_function_without_state() -> None:
        counter["value"] += 1

    def sync_function_with_state(state: State) -> None:
        assert state is not None
        assert isinstance(state, State)
        counter["value"] += 1
        state.x = True

    async def async_function_with_state(state: State) -> None:
        assert state is not None
        assert isinstance(state, State)
        counter["value"] += 1
        state.y = True

    with create_test_client(
        [],
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
        app = cast(Starlite, client.app)
        assert app.state.x
        assert app.state.y
        counter["value"] = 0
        assert counter["value"] == 0
    assert counter["value"] == 4
