from litestar.datastructures import State
from litestar.types import Message


async def before_send(message: Message, state: State) -> None: ...
