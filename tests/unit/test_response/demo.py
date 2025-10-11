from collections.abc import AsyncIterator

from anyio import Path, open_file, sleep
from msgspec import Struct

from litestar import Litestar, post
from litestar.response import ServerSentEvent
from litestar.response.streaming import ClientDisconnectError


class CleanupRequest(Struct):
    file_path: str
    file_content: str


@post("/cleanup")
async def get_notified(data: CleanupRequest) -> ServerSentEvent:
    async with await open_file(data.file_path, "w") as file:
        await file.write(data.file_content)

    async def generator() -> AsyncIterator[str]:
        try:
            for _ in range(10):
                yield data.file_content
                await sleep(0.1)
        except ClientDisconnectError:
            await Path(data.file_path).unlink()

    return ServerSentEvent(generator())


def create_test_app() -> Litestar:
    return Litestar(route_handlers=[get_notified])


app = create_test_app()
