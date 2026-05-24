from typing import Any

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.params import MultipartBody


@post(path="/")
async def handle_file_upload(
    data: MultipartBody[list[UploadFile]],
) -> dict[str, tuple[str, str, Any]]:
    result = {}
    for file in data:
        content = await file.read()
        result[file.filename] = (len(content), file.content_type, file.headers)

    return result


app = Litestar(route_handlers=[handle_file_upload])
