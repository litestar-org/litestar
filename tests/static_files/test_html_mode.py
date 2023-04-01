from typing import TYPE_CHECKING

import pytest
from fsspec.implementations.local import LocalFileSystem

from litestar.file_system import BaseLocalFileSystem
from litestar.static_files.config import StaticFilesConfig
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from pathlib import Path

    from litestar.types import FileSystemProtocol


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), LocalFileSystem()))
def test_staticfiles_is_html_mode(tmpdir: "Path", file_system: "FileSystemProtocol") -> None:
    path = tmpdir / "index.html"
    path.write_text("content", "utf-8")
    static_files_config = StaticFilesConfig(
        path="/static", directories=[tmpdir], html_mode=True, file_system=file_system
    )
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert response.headers["content-disposition"].startswith("inline")


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), LocalFileSystem()))
def test_staticfiles_is_html_mode_serves_404_when_present(tmpdir: "Path", file_system: "FileSystemProtocol") -> None:
    path = tmpdir / "404.html"
    path.write_text("not found", "utf-8")
    static_files_config = StaticFilesConfig(
        path="/static", directories=[tmpdir], html_mode=True, file_system=file_system
    )
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.text == "not found"
        assert response.headers["content-type"] == "text/html; charset=utf-8"


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), LocalFileSystem()))
def test_staticfiles_is_html_mode_raises_exception_when_no_404_html_is_present(
    tmpdir: "Path", file_system: "FileSystemProtocol"
) -> None:
    static_files_config = StaticFilesConfig(
        path="/static", directories=[tmpdir], html_mode=True, file_system=file_system
    )
    with create_test_client([], static_files_config=[static_files_config]) as client:
        response = client.get("/static")
        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {"status_code": 404, "detail": "no file or directory match the path . was found"}
