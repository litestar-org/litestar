import os
from os import stat
from typing import TYPE_CHECKING

import pytest
from fsspec.implementations.local import LocalFileSystem

from starlite import File, create_test_client, get
from starlite.status_codes import HTTP_200_OK
from starlite.utils.file import BaseLocalFileSystem

if TYPE_CHECKING:
    from pathlib import Path

    from starlite.types import FileSystemProtocol


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
        return File(filename="text.txt", path=path, file_system=fs, file_info=fs_info)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"
        assert response.headers.get("content-disposition") == 'attachment; filename="text.txt"'


def test_file_with_passed_in_stat_result(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    fs = LocalFileSystem()
    stat_result = stat(path)  # noqa:PL116

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
