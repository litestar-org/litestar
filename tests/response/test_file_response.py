"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are
meant to ensure our compatibility with their API.
"""
from email.utils import formatdate
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

import anyio
import pytest

from starlite import BackgroundTask, ImproperlyConfiguredException
from starlite.connection import empty_send
from starlite.response import FileResponse
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


def test_file_response(tmpdir: Path) -> None:
    path = tmpdir / "xyz"
    content = b"<file content>" * 1000
    Path(path).write_bytes(content)
    date_string = formatdate(Path(path).stat().st_mtime, usegmt=True)

    filled_by_bg_task = ""

    async def numbers(minimum: int, maximum: int) -> AsyncIterator[str]:
        for i in range(minimum, maximum + 1):
            yield str(i)
            if i != maximum:
                yield ", "
            await anyio.sleep(0)

    async def numbers_for_cleanup(start: int = 1, stop: int = 5) -> None:
        nonlocal filled_by_bg_task
        async for thing in numbers(start, stop):
            filled_by_bg_task = filled_by_bg_task + thing

    cleanup_task = BackgroundTask(numbers_for_cleanup, start=6, stop=9)

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        response = FileResponse(path=path, filename="example.png", background=cleanup_task)
        await response(scope, receive, send)

    assert filled_by_bg_task == ""
    client = TestClient(app)
    response = client.get("/")
    expected_disposition = 'attachment; filename="example.png"'
    assert response.status_code == HTTP_200_OK
    assert response.content == content
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == expected_disposition
    assert response.headers["content-length"] == "14000"
    assert response.headers["last-modified"].lower() == date_string.lower()
    assert "etag" in response.headers
    assert filled_by_bg_task == "6, 7, 8, 9"


async def test_file_response_with_directory_raises_error(tmpdir: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        await FileResponse(path=tmpdir, filename="example.png").start_response(empty_send)


async def test_file_response_with_missing_file_raises_error(tmpdir: Path) -> None:
    path = tmpdir / "404.txt"
    with pytest.raises(ImproperlyConfiguredException):
        await FileResponse(path=path, filename="404.txt").start_response(empty_send)


def test_file_response_with_chinese_filename(tmpdir: Path) -> None:
    content = b"file content"
    filename = "你好.txt"
    path = tmpdir / filename
    Path(path).write_bytes(content)
    app = FileResponse(path=path, filename=filename)
    client = TestClient(app)
    response = client.get("/")
    expected_disposition = "attachment; filename*=utf-8''%E4%BD%A0%E5%A5%BD.txt"
    assert response.status_code == HTTP_200_OK
    assert response.content == content
    assert response.headers["content-disposition"] == expected_disposition


def test_file_response_with_inline_disposition(tmpdir: Path) -> None:
    content = b"file content"
    filename = "hello.txt"
    path = tmpdir / filename
    Path(path).write_bytes(content)
    app = FileResponse(path=path, filename=filename, content_disposition_type="inline")
    client = TestClient(app)
    response = client.get("/")
    expected_disposition = 'inline; filename="hello.txt"'
    assert response.status_code == HTTP_200_OK
    assert response.content == content
    assert response.headers["content-disposition"] == expected_disposition


def test_file_response_known_size(tmpdir: Path) -> None:
    path = tmpdir / "xyz"
    content = b"<file content>" * 1000
    Path(path).write_bytes(content)
    app = FileResponse(path=path, filename="example.png")
    client: TestClient = TestClient(app)
    response = client.get("/")
    assert response.headers["content-length"] == str(len(content))
