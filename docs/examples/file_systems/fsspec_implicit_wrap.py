import fsspec

from litestar import Litestar, get
from litestar.response import File

s3_fs = fsspec.filesystem("s3", asynchronous=True)


@get("/{file_name:str}")
async def file_handler(file_name: str) -> File:
    return File(file_name, file_system=s3_fs)


app = Litestar([file_handler])
