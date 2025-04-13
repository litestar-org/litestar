from typing import Any, Dict, List, Tuple

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body


@post(path="/")
async def handle_file_upload(
    data: Annotated[List[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Dict[str, Tuple[str, str, Any]]:
    result = {}

    for file in data:
        content = await file.read()
        result[file.filename] = (len(content), file.content_type, file.headers)

    return result


app = Litestar(route_handlers=[handle_file_upload])
