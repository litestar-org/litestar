from typing import Dict

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body


@post(path="/")
async def handle_file_upload(
    data: Annotated[
        Dict[str, UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)
    ],
) -> Dict[str, str]:
    file_contents = {}
    for name, file in data.items():
        content = await file.read()
        file_contents[name] = content.decode()

    return file_contents


app = Litestar(route_handlers=[handle_file_upload])
