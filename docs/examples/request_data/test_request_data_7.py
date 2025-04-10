from hashlib import sha256

from typing_extensions import Annotated

from litestar import Litestar, MediaType, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.testing import TestClient


@post(path="/", media_type=MediaType.TEXT, sync_to_thread=False)
def handle_file_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> str:
    content = data.file.read()
    filename = data.filename
    return f"{filename}, {sha256(content).hexdigest()}"


app = Litestar(route_handlers=[handle_file_upload])


def test_file_upload() -> None:
    with TestClient(app) as client:
        response = client.post("/", files={"file": ("hello.txt", b"hello")})
        assert response.status_code == 201
        assert response.text == "hello.txt, " + sha256(b"hello").hexdigest()
