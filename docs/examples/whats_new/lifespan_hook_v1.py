from litestar.datastructures import State


def on_startup(state: State) -> None:
    print(state.something)
