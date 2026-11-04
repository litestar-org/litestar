from typing import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body


@post("/upload/")
async def upload_file(
    data: Annotated[list[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, list[str | None]]:
    return {"file_names": [file.filename for file in data]}


app = Litestar(route_handlers=[upload_file])
