import io
from dataclasses import dataclass
from hashlib import sha256

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.testing import TestClient


@dataclass
class User:
    id: int
    name: str
    form_input_name: UploadFile


@post(path="/")
async def create_user(
    data: Annotated[User, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> dict[str, str]:
    content = await data.form_input_name.read()
    filename = data.form_input_name.filename
    return {"id": data.id, "name": data.name, "filename": filename, "file_content": sha256(content).hexdigest()}


app = Litestar(route_handlers=[create_user], debug=True)


def test_create_user() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/", files={"form_input_name": ("filename", io.BytesIO(b"file content"))}, data={"id": 1, "name": "johndoe"}
        )
        assert response.status_code == 201
        assert response.json().get("name") == "johndoe"
        assert response.json().get("id") == 1
        assert response.json().get("filename") == "filename"
        assert response.json().get("file_content") == sha256(b"file content").hexdigest()
