from litestar import Litestar, Request, get
from litestar.file_system import FileSystemRegistry


@get("/")
async def handler(request: Request) -> bytes:
    registry = request.app.plugins.get(FileSystemRegistry)
    return registry.default.read_bytes("some/file.txt")


app = Litestar([handler])
