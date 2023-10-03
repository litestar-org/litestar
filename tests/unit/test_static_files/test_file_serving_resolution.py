import gzip
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

import brotli
import pytest
from fsspec.implementations.local import LocalFileSystem

from litestar import MediaType, get
from litestar.file_system import BaseLocalFileSystem
from litestar.static_files.config import StaticFilesConfig
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types import FileSystemProtocol


def test_default_static_files_config(tmpdir: "Path") -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")
    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])

    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK, response.text
        assert response.text == "content"


def test_multiple_static_files_configs(tmpdir: "Path") -> None:
    root1 = tmpdir.mkdir("1")  # type: ignore
    root2 = tmpdir.mkdir("2")  # type: ignore
    path1 = root1 / "test.txt"  # pyright: ignore
    path1.write_text("content1", "utf-8")
    path2 = root2 / "test.txt"  # pyright: ignore
    path2.write_text("content2", "utf-8")

    static_files_config = [
        StaticFilesConfig(path="/static_first", directories=[root1]),  # pyright: ignore
        StaticFilesConfig(path="/static_second", directories=[root2]),  # pyright: ignore
    ]
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static_first/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content1"

        response = client.get("/static_second/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content2"


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), LocalFileSystem()))
def test_static_files_configs_with_mixed_file_systems(tmpdir: "Path", file_system: "FileSystemProtocol") -> None:
    root1 = tmpdir.mkdir("1")  # type: ignore
    root2 = tmpdir.mkdir("2")  # type: ignore
    path1 = root1 / "test.txt"  # pyright: ignore
    path1.write_text("content1", "utf-8")
    path2 = root2 / "test.txt"  # pyright: ignore
    path2.write_text("content2", "utf-8")

    static_files_config = [
        StaticFilesConfig(path="/static_first", directories=[root1], file_system=file_system),  # pyright: ignore
        StaticFilesConfig(path="/static_second", directories=[root2]),  # pyright: ignore
    ]
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static_first/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content1"

        response = client.get("/static_second/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content2"


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), LocalFileSystem()))
def test_static_files_config_with_multiple_directories(tmpdir: "Path", file_system: "FileSystemProtocol") -> None:
    root1 = tmpdir.mkdir("first")  # type: ignore
    root2 = tmpdir.mkdir("second")  # type: ignore
    path1 = root1 / "test1.txt"  # pyright: ignore
    path1.write_text("content1", "utf-8")
    path2 = root2 / "test2.txt"  # pyright: ignore
    path2.write_text("content2", "utf-8")

    with create_test_client(
        [],
        static_files_config=[
            StaticFilesConfig(path="/static", directories=[root1, root2], file_system=file_system)  # pyright: ignore
        ],
    ) as client:
        response = client.get("/static/test1.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content1"

        response = client.get("/static/test2.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content2"


def test_staticfiles_for_slash_path_regular_mode(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    static_files_config = StaticFilesConfig(path="/", directories=[tmpdir])
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/text.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


def test_staticfiles_for_slash_path_html_mode(tmpdir: "Path") -> None:
    path = tmpdir / "index.html"
    path.write_text("<html></html>", "utf-8")

    static_files_config = StaticFilesConfig(path="/", directories=[tmpdir], html_mode=True)
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "<html></html>"


def test_sub_path_under_static_path(tmpdir: "Path") -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    @get("/static/sub/{f:str}", media_type=MediaType.TEXT)
    def handler(f: str) -> str:
        return f

    with create_test_client(
        handler, static_files_config=[StaticFilesConfig(path="/static", directories=[tmpdir])]
    ) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK

        response = client.get("/static/sub/abc")
        assert response.status_code == HTTP_200_OK


def test_static_substring_of_self(tmpdir: "Path") -> None:
    path = tmpdir.mkdir("static_part").mkdir("static") / "test.txt"  # type: ignore
    path.write_text("content", "utf-8")

    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static/static_part/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


@pytest.mark.parametrize("extension", ["css", "js", "html", "json"])
def test_static_files_response_mimetype(tmpdir: "Path", extension: str) -> None:
    fn = f"test.{extension}"
    path = tmpdir / fn
    path.write_text("content", "utf-8")
    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    expected_mime_type = mimetypes.guess_type(fn)[0]

    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get(f"/static/{fn}")
        assert expected_mime_type
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(expected_mime_type)


@pytest.mark.parametrize("extension", ["gz", "br"])
def test_static_files_response_encoding(tmp_path: "Path", extension: str) -> None:
    fn = f"test.js.{extension}"
    path = tmp_path / fn
    compressed_data = None
    if extension == "br":
        compressed_data = brotli.compress(b"content")
    elif extension == "gz":
        compressed_data = gzip.compress(b"content")
    path.write_bytes(compressed_data)  # type: ignore[arg-type]
    static_files_config = StaticFilesConfig(path="/static", directories=[tmp_path])
    expected_encoding_type = mimetypes.guess_type(fn)[1]

    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get(f"/static/{fn}")
        assert expected_encoding_type
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-encoding"].startswith(expected_encoding_type)


@pytest.mark.parametrize("send_as_attachment,disposition", [(True, "attachment"), (False, "inline")])
def test_static_files_content_disposition(tmpdir: "Path", send_as_attachment: bool, disposition: str) -> None:
    path = tmpdir.mkdir("static_part").mkdir("static") / "test.txt"  # type: ignore
    path.write_text("content", "utf-8")

    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir], send_as_attachment=send_as_attachment)

    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static/static_part/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-disposition"].startswith(disposition)


def test_service_from_relative_path_using_string(tmpdir: "Path") -> None:
    sub_dir = Path(tmpdir.mkdir("low")).resolve()  # type: ignore

    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    static_files_config = StaticFilesConfig(path="/static", directories=[f"{sub_dir}/.."])
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


def test_service_from_relative_path_using_path(tmpdir: "Path") -> None:
    sub_dir = Path(tmpdir.mkdir("low")).resolve()  # type: ignore

    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    static_files_config = StaticFilesConfig(path="/static", directories=[Path(f"{sub_dir}/..")])
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


def test_service_from_base_path_using_string(tmpdir: "Path") -> None:
    sub_dir = Path(tmpdir.mkdir("low")).resolve()  # type: ignore

    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    @get("/", media_type=MediaType.TEXT)
    def index_handler() -> str:
        return "index"

    @get("/sub")
    def sub_handler() -> dict:
        return {"hello": "world"}

    static_files_config = StaticFilesConfig(path="/", directories=[f"{sub_dir}/.."])
    with create_test_client([index_handler, sub_handler], static_files_config=[static_files_config]) as client:
        response = client.get("/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"

        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "index"

        response = client.get("/sub")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"hello": "world"}
