from typing import Annotated

from litestar import Litestar, MediaType, post
from litestar.datastructures import UploadFile
from litestar.params import MultipartBody


@post(path="/", media_type=MediaType.TEXT)
async def handle_file_upload(data: MultipartBody[UploadFile]) -> str:
    content = await data.read()
    filename = data.filename
    return f"{filename},length: {len(content)}"


app = Litestar(route_handlers=[handle_file_upload])
