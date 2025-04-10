from hashlib import sha256
from typing import Dict

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.testing import TestClient


@post(path="/")
async def handle_file_upload(
    data: Annotated[Dict[str, UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Dict[str, str]:
    file_contents = {}
    for name, file in data.items():
        content = await file.read()
        file_contents[file.filename] = sha256(content).hexdigest()

    return file_contents


app = Litestar(route_handlers=[handle_file_upload])


def test_file_upload() -> None:
    with TestClient(app) as client:
        response = client.post("/", files={"file": ("hello.txt", b"hello")})
        assert response.status_code == 201
        assert response.json().get("hello.txt") == sha256(b"hello").hexdigest()
