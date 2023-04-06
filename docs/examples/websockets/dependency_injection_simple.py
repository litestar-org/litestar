from starlite import Starlite, websocket_listener
from starlite.di import Provide


def some_dependency() -> str:
    return "hello"


@websocket_listener("/", dependencies={"some": Provide(some_dependency)})
async def handler(data: str, some: str) -> str:
    return data + some


app = Starlite([handler])
