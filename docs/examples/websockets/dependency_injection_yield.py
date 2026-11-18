from collections.abc import AsyncIterator
from typing import TypedDict

from litestar import Litestar, websocket_listener
from litestar.datastructures import State
from litestar.di import NamedDependency, Provide


class Message(TypedDict):
    message: str
    client_count: int


async def socket_client_count(state: State) -> AsyncIterator[int]:
    if not hasattr(state, "count"):
        state.count = 0

    state.count += 1
    yield state.count
    state.count -= 1


@websocket_listener("/", dependencies={"client_count": Provide(socket_client_count)})
async def handler(data: str, client_count: NamedDependency[int]) -> Message:
    return Message(message=data, client_count=client_count)


app = Litestar([handler])
