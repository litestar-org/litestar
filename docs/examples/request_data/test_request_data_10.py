import io
from hashlib import sha256
from typing import Any, Dict, List, Tuple

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.testing import TestClient


@post(path="/")
async def handle_file_upload(
    data: Annotated[List[UploadFile], Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Dict[str, Tuple[str, str, Any]]:
    result = {}

    for file in data:
        content = await file.read()
        result[file.filename] = (sha256(content).hexdigest(), file.content_type, file.headers)

    return result


app = Litestar(route_handlers=[handle_file_upload])


def test_file_upload() -> None:
    with TestClient(app) as client:
        # if you pass a dict to the `files` parameter without specifying a filename, it will default to `upload`
        #     # file (or bytes)
        response = client.post(
            "/",
            files={"will default to upload": io.BytesIO(b"hello"), "will default to upload also": io.BytesIO(b"world")},
        )
        assert response.status_code == 201
        assert response.json().get("upload")[0] != sha256(b"hello").hexdigest()
        assert response.json().get("upload")[0] == sha256(b"world").hexdigest()

        # if you pass the filename explicitly, it will be used as the filename
        #     # (filename, file (or bytes))
        response = client.post("/", files={"file": ("hello.txt", io.BytesIO(b"hello"))})
        assert response.status_code == 201
        assert response.json().get("hello.txt")[0] == sha256(b"hello").hexdigest()

        # if you add the content type, it will be used as the content type
        #     # (filename, file (or bytes), content_type)
        response = client.post("/", files={"file": ("hello.txt", io.BytesIO(b"hello"), "application/x-bittorrent")})
        assert response.status_code == 201
        assert response.json().get("hello.txt")[0] == sha256(b"hello").hexdigest()
        assert response.json().get("hello.txt")[1] == "application/x-bittorrent"

        # finally you can specify headers like so
        #     # (filename, file (or bytes), content_type, headers)
        response = client.post(
            "/", files={"file": ("hello.txt", io.BytesIO(b"hello"), "application/x-bittorrent", {"X-Foo": "bar"})}
        )
        assert response.status_code == 201
        assert response.json().get("hello.txt")[0] == sha256(b"hello").hexdigest()
        assert response.json().get("hello.txt")[1] == "application/x-bittorrent"
        assert ("X-Foo", "bar") in response.json().get("hello.txt")[2].items()
