from typing import Any, Dict

from pydantic import BaseConfig, BaseModel
from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body


class FormData(BaseModel):
    cv: UploadFile
    diploma: UploadFile

    class Config(BaseConfig):
        arbitrary_types_allowed = True


@post(path="/")
async def handle_file_upload(
    data: Annotated[FormData, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Dict[str, Any]:
    cv_content = await data.cv.read()
    diploma_content = await data.diploma.read()

    return {"cv": cv_content.decode(), "diploma": diploma_content.decode()}


app = Litestar(route_handlers=[handle_file_upload])
