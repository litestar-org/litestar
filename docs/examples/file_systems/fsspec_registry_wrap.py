import fsspec

from litestar import Litestar, get
from litestar.file_system import FileSystemRegistry
from litestar.response import File


@get("/{file_name:str}")
async def file_handler(file_name: str) -> File:
    return File(file_name, file_system="s3")


app = Litestar(
    [file_handler],
    plugins=[
        FileSystemRegistry({"s3": fsspec.filesystem("s3", asynchronous=True)}),
    ],
)
