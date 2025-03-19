import fsspec

from litestar import Litestar, get
from litestar.file_system import FileSystemRegistry
from litestar.response import File


@get("/{file_name:str}")
async def file_handler(file_name: str) -> File:
    return File(file_name, file_system="assets")


def create_app(assets_fs: fsspec.AbstractFileSystem):
    return Litestar(
        [file_handler],
        plugins=[FileSystemRegistry({"assets": assets_fs})],
    )
