from litestar.datastructures import State
from litestar.types import Message, Scope


async def before_send(message: Message, state: State, scope: Scope) -> None: ...
