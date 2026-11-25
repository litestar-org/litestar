from litestar import Litestar, websocket_listener
from litestar.di import NamedDependency, provide


@provide(key="some", sync_to_thread=False)
def some_dependency() -> str:
    return "hello"


@websocket_listener("/", dependencies=[some_dependency])
async def handler(data: str, some: NamedDependency[str]) -> str:
    return data + some


app = Litestar([handler])
