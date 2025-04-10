from base64 import urlsafe_b64encode
from typing import Dict

from pydantic import BaseModel, ConfigDict
from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.testing import TestClient


class FormData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    cv: UploadFile
    diploma: UploadFile


@post(path="/")
async def handle_file_upload(
    data: Annotated[FormData, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Dict[str, str]:
    cv_content = await data.cv.read()
    diploma_content = await data.diploma.read()

    return {"cv": cv_content.decode(), "diploma": diploma_content.decode(), "what is it": cv_content}


app = Litestar(route_handlers=[handle_file_upload])


def test_file_upload() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/", files={"cv": ("cv.txt", b"cv content"), "diploma": ("diploma.txt", b"diploma content")}
        )
        assert response.status_code == 201
        assert response.json() == {
            "cv": "cv content",
            "diploma": "diploma content",
            "what is it": urlsafe_b64encode(b"cv content").decode(),
        }
