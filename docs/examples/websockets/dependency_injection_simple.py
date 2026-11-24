from litestar import Litestar, websocket_listener
from litestar.di import NamedDependency, Provide


def some_dependency() -> str:
    return "hello"


@websocket_listener("/", dependencies={"some": Provide(some_dependency, sync_to_thread=False)})
async def handler(data: str, some: NamedDependency[str]) -> str:
    return data + some


app = Litestar([handler])
