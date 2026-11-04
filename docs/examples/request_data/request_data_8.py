import dataclasses

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.params import MultipartBody


@dataclasses.dataclass()
class FormData:
    cv: UploadFile
    diploma: UploadFile


@post(path="/")
async def handle_file_upload(
    data: MultipartBody[FormData],
) -> dict[str, str]:
    cv_content = await data.cv.read()
    diploma_content = await data.diploma.read()

    return {"cv": cv_content.decode(), "diploma": diploma_content.decode()}


app = Litestar(route_handlers=[handle_file_upload])
