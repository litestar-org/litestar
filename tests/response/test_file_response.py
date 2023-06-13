from email.utils import formatdate
from os import urandom
from pathlib import Path
from typing import Any

import pytest

from litestar import get
from litestar.connection.base import empty_send
from litestar.exceptions import ImproperlyConfiguredException
from litestar.file_system import BaseLocalFileSystem, FileSystemAdapter
from litestar.response.file import ASGIFileResponse, FileResponse, async_file_iterator
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


@pytest.mark.parametrize("content_disposition_type", ("inline", "attachment"))
def test_file_response_default_content_type(tmpdir: Path, content_disposition_type: Any) -> None:
    path = Path(tmpdir / "image.png")
    path.write_bytes(b"")

    @get("/")
    def handler() -> FileResponse:
        return FileResponse(path=path, content_disposition_type=content_disposition_type)

    with create_test_client(handler, debug=True, openapi_config=None) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"] == f'{content_disposition_type}; filename=""'


@pytest.mark.parametrize("content_disposition_type", ("inline", "attachment"))
def test_file_response_infer_content_type(tmpdir: Path, content_disposition_type: Any) -> None:
    path = Path(tmpdir / "image.png")
    path.write_bytes(b"")

    @get("/")
    def handler() -> FileResponse:
        return FileResponse(path=path, filename="image.png", content_disposition_type=content_disposition_type)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"] == "image/png"
        assert response.headers["content-disposition"] == f'{content_disposition_type}; filename="image.png"'


@pytest.mark.parametrize("filename, expected", (("Jacky Chen", "Jacky%20Chen"), ("成龍", "%E6%88%90%E9%BE%8D")))
def test_filename(tmpdir: Path, filename: str, expected: str) -> None:
    path = Path(tmpdir / f"{filename}.txt")
    path.write_bytes(b"")

    @get("/")
    def handler() -> FileResponse:
        return FileResponse(path=path, filename=f"{filename}.txt")

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-disposition"] == f"attachment; filename*=utf-8''{expected}.txt"


def test_file_response_content_length(tmpdir: Path) -> None:
    content = urandom(1024 * 10)
    path = Path(tmpdir / "file.txt")
    path.write_bytes(content)

    @get("/")
    def handler() -> FileResponse:
        return FileResponse(path=path)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.content == content
        assert response.headers["content-length"] == str(len(content))


def test_file_response_last_modified(tmpdir: Path) -> None:
    path = Path(tmpdir / "file.txt")
    path.write_bytes(b"")

    @get("/")
    def handler() -> FileResponse:
        return FileResponse(path=path, filename="image.png")

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.headers["last-modified"].lower() == formatdate(path.stat().st_mtime, usegmt=True).lower()


async def test_file_response_with_directory_raises_error(tmpdir: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        asgi_response = ASGIFileResponse(file_path=tmpdir, filename="example.png")
        await asgi_response.start_response(empty_send)


async def test_file_response_with_missing_file_raises_error(tmpdir: Path) -> None:
    path = tmpdir / "404.txt"
    with pytest.raises(ImproperlyConfiguredException):
        asgi_response = ASGIFileResponse(file_path=path, filename="404.txt")
        await asgi_response.start_response(empty_send)


@pytest.mark.parametrize("chunk_size", [4, 8, 16, 256, 512, 1024, 2048])
async def test_file_iterator(tmpdir: Path, chunk_size: int) -> None:
    content = urandom(1024)
    path = Path(tmpdir / "file.txt")
    path.write_bytes(content)
    result = b"".join(
        [
            chunk
            async for chunk in async_file_iterator(
                file_path=path, chunk_size=chunk_size, adapter=FileSystemAdapter(BaseLocalFileSystem())
            )
        ]
    )
    assert result == content


@pytest.mark.parametrize("size", (1024, 2048, 4096, 1024 * 10, 2048 * 10, 4096 * 10))
def test_large_files(tmpdir: Path, size: int) -> None:
    content = urandom(1024 * size)
    path = Path(tmpdir / "file.txt")
    path.write_bytes(content)

    @get("/")
    def handler() -> FileResponse:
        return FileResponse(path=path)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.content == content
        assert response.headers["content-length"] == str(len(content))
