import os
from inspect import iscoroutine
from os import stat
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pytest
from fsspec.implementations.local import LocalFileSystem

from litestar import get
from litestar.datastructures import ETag
from litestar.exceptions import ImproperlyConfiguredException
from litestar.file_system import BaseLocalFileSystem
from litestar.response_containers import File, Redirect
from litestar.status_codes import HTTP_200_OK
from litestar.testing import RequestFactory, create_test_client

if TYPE_CHECKING:
    from litestar.types import FileSystemProtocol


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), LocalFileSystem()))
def test_file_with_different_file_systems(tmpdir: "Path", file_system: "FileSystemProtocol") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    @get("/", media_type="application/octet-stream")
    def handler() -> File:
        return File(
            filename="text.txt",
            path=path,
            file_system=file_system,
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"
        assert response.headers.get("content-disposition") == 'attachment; filename="text.txt"'


def test_file_with_passed_in_file_info(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    fs = LocalFileSystem()
    fs_info = fs.info(tmpdir / "text.txt")

    assert fs_info

    @get("/", media_type="application/octet-stream")
    def handler() -> File:
        return File(filename="text.txt", path=path, file_system=fs, file_info=fs_info)  # pyright: ignore

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK, response.text
        assert response.text == "content"
        assert response.headers.get("content-disposition") == 'attachment; filename="text.txt"'


def test_file_with_passed_in_stat_result(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    fs = LocalFileSystem()
    stat_result = stat(path)

    @get("/", media_type="application/octet-stream")
    def handler() -> File:
        return File(filename="text.txt", path=path, file_system=fs, stat_result=stat_result)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"
        assert response.headers.get("content-disposition") == 'attachment; filename="text.txt"'


async def test_file_with_symbolic_link(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    linked = tmpdir / "alt.txt"
    os.symlink(path, linked, target_is_directory=False)

    fs = BaseLocalFileSystem()
    file_info = await fs.info(linked)

    assert file_info["islink"]

    @get("/", media_type="application/octet-stream")
    def handler() -> File:
        return File(filename="alt.txt", path=linked, file_system=fs, file_info=file_info)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"
        assert response.headers.get("content-disposition") == 'attachment; filename="alt.txt"'


async def test_file_sets_etag_correctly(tmpdir: "Path") -> None:
    request = RequestFactory().get()

    path = tmpdir / "file.txt"
    content = b"<file content>"
    Path(path).write_bytes(content)

    etag = ETag(value="special")
    file_container = File(path=path, etag=etag)
    response = file_container.to_response(
        status_code=HTTP_200_OK, media_type=None, headers={}, app=request.app, request=request
    )
    if iscoroutine(response.file_info):
        await response.file_info
    assert response.etag == etag


def test_file_system_validation(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    class FSWithoutOpen:
        def info(self) -> None:
            return

    with pytest.raises(ImproperlyConfiguredException):
        File(
            filename="text.txt",
            path=path,
            file_system=FSWithoutOpen(),
        )

    class FSWithoutInfo:
        def open(self) -> None:
            return

    with pytest.raises(ImproperlyConfiguredException):
        File(
            filename="text.txt",
            path=path,
            file_system=FSWithoutInfo(),
        )

    class ImplementedFS:
        def info(self) -> None:
            return

        def open(self) -> None:
            return

    assert File(
        filename="text.txt",
        path=path,
        file_system=ImplementedFS(),
    )


@pytest.mark.parametrize(
    "status_code,expected_status_code",
    [
        (301, 301),
        (302, 302),
        (303, 303),
        (307, 307),
        (308, 308),
    ],
)
def test_redirect_dynamic_status_code(status_code: Optional[int], expected_status_code: int) -> None:
    @get("/")
    def handler() -> Redirect:
        return Redirect(path="/something-else", status_code=status_code)  # type: ignore[arg-type]

    with create_test_client([handler]) as client:
        res = client.get("/", follow_redirects=False)
        assert res.status_code == expected_status_code


@pytest.mark.parametrize("handler_status_code", [301, 307, None])
def test_redirect(handler_status_code: Optional[int]) -> None:
    @get("/", status_code=handler_status_code)
    def handler() -> Redirect:
        return Redirect(path="/something-else", status_code=301)

    with create_test_client([handler]) as client:
        res = client.get("/", follow_redirects=False)
        assert res.status_code == 301
