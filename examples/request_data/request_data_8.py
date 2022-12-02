from typing import Dict
from pydantic import BaseModel, BaseConfig
from starlite import Body, RequestEncodingType, UploadFile, post, Starlite


class FormData(BaseModel):
    cv: UploadFile
    diploma: UploadFile

    class Config(BaseConfig):
        arbitrary_types_allowed = True


@post(path="/")
async def handle_file_upload(
    data: FormData = Body(media_type=RequestEncodingType.MULTI_PART),
) -> Dict:
    cv_content = await data.cv.read()
    diploma_content = await data.diploma.read()

    return {"cv": cv_content.decode(), "diploma": diploma_content.decode()}


app = Starlite(route_handlers=[handle_file_upload])
