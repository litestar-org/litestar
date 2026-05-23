from typing import Dict

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.params import MultipartBody


@post(path="/")
async def handle_file_upload(
    data: MultipartBody[Dict[str, UploadFile]],
) -> Dict[str, str]:
    file_contents = {}
    for name, file in data.items():
        content = await file.read()
        file_contents[file.filename] = len(content)

    return file_contents


app = Litestar(route_handlers=[handle_file_upload])
