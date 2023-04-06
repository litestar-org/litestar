from typing import TypedDict

from starlite import Starlite, websocket_listener
from starlite.datastructures import State
from starlite.di import Provide


class Message(TypedDict):
    message: str
    client_count: int


def socket_client_count(state: State) -> int:
    if not hasattr(state, "count"):
        state.count = 0

    state.count += 1
    yield state.count
    state.count -= 1


@websocket_listener("/", dependencies={"client_count": Provide(socket_client_count)})
async def handler(data: str, client_count: int) -> Message:
    return Message(message=data, client_count=client_count)


app = Starlite([handler])
