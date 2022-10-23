from pathlib import Path

from starlite import File
from starlite.datastructures import ETag
from starlite.status_codes import HTTP_200_OK
from starlite.testing import RequestFactory

request = RequestFactory().get(path="/")


def test_file_sets_etag_correctly(tmpdir: Path) -> None:
    path = tmpdir / "file.txt"
    content = b"<file content>"
    Path(path).write_bytes(content)

    etag = ETag(value="special")
    file_container = File(path=path, etag=etag)
    response = file_container.to_response(
        status_code=HTTP_200_OK, media_type=None, headers={}, app=request.app, request=request
    )
    assert response.headers["etag"] == '"special"'
