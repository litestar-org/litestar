import fsspec

from litestar import Litestar, get
from litestar.file_system import FsspecAsyncWrapper
from litestar.response import File

wrapped_s3_fs = FsspecAsyncWrapper(fsspec.filesystem("s3", asynchronous=True))


@get("/{file_name:str}")
async def file_handler(file_name: str) -> File:
    return File(file_name, file_system=wrapped_s3_fs)


app = Litestar([file_handler])
