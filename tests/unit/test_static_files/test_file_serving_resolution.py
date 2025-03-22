from __future__ import annotations

import gzip
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

import brotli
import pytest
from fsspec.implementations.local import LocalFileSystem
from pytest_mock import MockerFixture

from litestar import MediaType, get
from litestar.file_system import BaseFileSystem, BaseLocalFileSystem, FileSystemRegistry, maybe_wrap_fsspec_file_system
from litestar.static_files import _get_fs_info, create_static_files_router
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client
from tests.unit.test_response.test_file_response import MockFileSystem

if TYPE_CHECKING:
    pass


def test_default_static_files_router(tmpdir: Path) -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    with create_test_client([create_static_files_router(path="/static", directories=[tmpdir])]) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK, response.text
        assert response.text == "content"


def test_default_file_system(tmpdir: Path) -> None:
    with create_test_client(
        [create_static_files_router(path="/static", directories=[tmpdir])],
        plugins=[FileSystemRegistry(default=MockFileSystem())],
    ) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK, response.text
        assert response.text == str(tmpdir / "test.txt")


@pytest.fixture()
def setup_dirs(tmpdir: Path) -> tuple[Path, Path]:
    paths = []
    for i in range(1, 3):
        root = tmpdir / str(i)
        root.mkdir()
        file_path = root / f"test_{i}.txt"
        file_path.write_text(f"content{i}", "utf-8")
        paths.append(root)

    return paths[0], paths[1]


def test_multiple_static_files_routers(setup_dirs: tuple[Path, Path]) -> None:
    root1, root2 = setup_dirs

    with create_test_client(
        [
            create_static_files_router(path="/static_first", directories=[root1]),
            create_static_files_router(path="/static_second", directories=[root2]),
        ]
    ) as client:
        response = client.get("/static_first/test_1.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content1"

        response = client.get("/static_second/test_2.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content2"


def test_static_files_routers_with_mixed_file_systems(
    file_system: BaseFileSystem, setup_dirs: tuple[Path, Path]
) -> None:
    root1, root2 = setup_dirs

    with create_test_client(
        [
            create_static_files_router(path="/static_first", directories=[root1], file_system=file_system),
            create_static_files_router(path="/static_second", directories=[root2]),
        ]
    ) as client:
        response = client.get("/static_first/test_1.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content1"

        response = client.get("/static_second/test_2.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content2"


def test_static_files_routers_with_multiple_directories(
    file_system: BaseFileSystem, setup_dirs: tuple[Path, Path]
) -> None:
    root1, root2 = setup_dirs

    with create_test_client(
        [create_static_files_router(path="/static", directories=[root1, root2], file_system=file_system)]
    ) as client:
        response = client.get("/static/test_1.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content1"

        response = client.get("/static/test_2.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content2"


def test_staticfiles_for_slash_path_regular_mode(tmpdir: Path) -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    with create_test_client([create_static_files_router(path="/", directories=[tmpdir])]) as client:
        response = client.get("/text.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


def test_staticfiles_for_slash_path_html_mode(
    tmpdir: Path,
) -> None:
    path = tmpdir / "index.html"
    path.write_text("<html></html>", "utf-8")

    with create_test_client([create_static_files_router(path="/", directories=[tmpdir], html_mode=True)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "<html></html>"


def test_sub_path_under_static_path(
    tmpdir: Path,
) -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    @get("/static/sub/{f:str}", media_type=MediaType.TEXT)
    def handler(f: str) -> str:
        return f

    with create_test_client([create_static_files_router(path="/static", directories=[tmpdir]), handler]) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK

        response = client.get("/static/sub/abc")
        assert response.status_code == HTTP_200_OK


def test_static_substring_of_self(
    tmpdir: Path,
) -> None:
    path = tmpdir.mkdir("static_part").mkdir("static") / "test.txt"  # type: ignore[arg-type, func-returns-value]
    path.write_text("content", "utf-8")

    with create_test_client([create_static_files_router(path="/static", directories=[tmpdir])]) as client:
        response = client.get("/static/static_part/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


@pytest.mark.parametrize("extension", ["css", "js", "html", "json"])
def test_static_files_response_mimetype(
    tmpdir: Path,
    extension: str,
) -> None:
    fn = f"test.{extension}"
    path = tmpdir / fn
    path.write_text("content", "utf-8")
    expected_mime_type = mimetypes.guess_type(fn)[0]

    with create_test_client([create_static_files_router(path="/static", directories=[tmpdir])]) as client:
        response = client.get(f"/static/{fn}")
        assert expected_mime_type
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-type"].startswith(expected_mime_type)


@pytest.mark.parametrize("extension", ["gz", "br"])
def test_static_files_response_encoding(
    tmp_path: Path,
    extension: str,
) -> None:
    fn = f"test.js.{extension}"
    path = tmp_path / fn
    compressed_data = None
    if extension == "br":
        compressed_data = brotli.compress(b"content")
    elif extension == "gz":
        compressed_data = gzip.compress(b"content")
    path.write_bytes(compressed_data)  # type: ignore[arg-type]
    expected_encoding_type = mimetypes.guess_type(fn)[1]

    with create_test_client([create_static_files_router(path="/static", directories=[tmp_path])]) as client:
        response = client.get(f"/static/{fn}")
        assert expected_encoding_type
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-encoding"].startswith(expected_encoding_type)


@pytest.mark.parametrize("send_as_attachment,disposition", [(True, "attachment"), (False, "inline")])
def test_static_files_content_disposition(
    tmpdir: Path,
    send_as_attachment: bool,
    disposition: str,
) -> None:
    path = tmpdir.mkdir("static_part").mkdir("static") / "test.txt"  # type: ignore[arg-type, func-returns-value]
    path.write_text("content", "utf-8")

    with create_test_client(
        [create_static_files_router(path="/static", directories=[tmpdir], send_as_attachment=send_as_attachment)]
    ) as client:
        response = client.get("/static/static_part/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.headers["content-disposition"].startswith(disposition)


def test_serve_from_relative_path_using_string(tmpdir: Path) -> None:
    sub_dir = Path(tmpdir.mkdir("low")).resolve()  # type: ignore[arg-type, func-returns-value]

    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    with create_test_client([create_static_files_router(path="/static", directories=[f"{sub_dir}/.."])]) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


def test_serve_from_relative_path_using_path(
    tmpdir: Path,
) -> None:
    sub_dir = Path(tmpdir.mkdir("low")).resolve()  # type: ignore[arg-type, func-returns-value]

    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    with create_test_client(
        [create_static_files_router(path="/static", directories=[Path(f"{sub_dir}/..")])]
    ) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "content"


@pytest.mark.parametrize("file_system", [BaseLocalFileSystem(), LocalFileSystem()])
@pytest.mark.parametrize("allow_symlinks_outside_directory", [True, False, None])
def test_allow_symlinks_outside_directory(
    tmp_path: Path,
    allow_symlinks_outside_directory: bool | None,
    tmp_path_factory: pytest.TempPathFactory,
    file_system: BaseFileSystem,
) -> None:
    static_file_dir = Path(tmp_path) / "static"
    static_file_dir.mkdir()

    source_file_path = tmp_path_factory.mktemp("test") / "test.txt"
    source_file_path.write_text("hello")

    linked_file_path = static_file_dir / "linked.txt"
    linked_file_path.symlink_to(source_file_path)

    if allow_symlinks_outside_directory is not None:
        router = create_static_files_router(
            path="/",
            directories=[static_file_dir],
            file_system=file_system,
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
        )
    else:
        router = create_static_files_router(
            path="/",
            directories=[static_file_dir],
            file_system=file_system,
        )

    with create_test_client(router) as client:
        if allow_symlinks_outside_directory:
            assert client.get("/linked.txt").status_code == 200
        else:
            assert client.get("/linked.txt").status_code == 404


@pytest.mark.parametrize("allow_symlinks_outside_directory", [True, False, None])
def test_allow_symlinks_outside_directory_internal_link(
    tmp_path: Path,
    allow_symlinks_outside_directory: bool | None,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    static_file_dir = tmp_path / "static"
    static_file_dir.mkdir()

    source_file_path = static_file_dir / "test.txt"
    source_file_path.write_text("hello")

    linked_file_path = static_file_dir / "linked.txt"
    linked_file_path.symlink_to(source_file_path.name)

    if allow_symlinks_outside_directory is not None:
        router = create_static_files_router(
            path="/",
            directories=[static_file_dir],
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
        )
    else:
        router = create_static_files_router(
            path="/",
            directories=[static_file_dir],
        )

    with create_test_client(router) as client:
        assert client.get("/linked.txt").status_code == 200


@pytest.mark.parametrize("allow_symlinks_outside_directory", [False, None])
def test_symlinked_file_without_symlink_resolution_support_on_file_system_raises(
    tmp_path: Path,
    allow_symlinks_outside_directory: bool | None,
    tmp_path_factory: pytest.TempPathFactory,
    mocker: MockerFixture,
) -> None:
    # if a path contains a symlink, but the file system does not support resolving
    # symlinks, we expect an internal error to be raised

    src_file = tmp_path / "source.txt"
    src_file.touch()

    linked_file = tmp_path / "linked.txt"
    linked_file.symlink_to(src_file)

    mocker.patch("litestar.file_system.LinkableFileSystem.get_symlink_resolver", return_value=None)

    if allow_symlinks_outside_directory is not None:
        router = create_static_files_router(
            path="/",
            directories=[tmp_path],
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
        )
    else:
        router = create_static_files_router(
            path="/",
            directories=[tmp_path],
        )

    with create_test_client(router, raise_server_exceptions=True) as client:
        res = client.get("/linked.txt")
        assert res.status_code == 500
        assert "does not support resolving symlinks" in res.text


@pytest.mark.skip
@pytest.mark.parametrize("allow_symlinks_outside_directory", [True, False])
def test_allow_symlinks_outside_directory_raises_on_non_linkable_file_system(
    tmp_path: Path,
    allow_symlinks_outside_directory: bool,
) -> None:
    with pytest.raises(TypeError, match="allow_symlinks_outside_directory"):
        create_static_files_router(
            path="/",
            directories=[tmp_path],
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
            file_system=LocalFileSystem(),
        )


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), maybe_wrap_fsspec_file_system(LocalFileSystem())))
@pytest.mark.parametrize("allow_symlinks_outside_directory", (True, False))
async def test_staticfiles_get_fs_info_no_access_to_non_static_directory(
    tmp_path: Path,
    file_system: BaseFileSystem,
    allow_symlinks_outside_directory: bool,
) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    index = tmp_path / "index.html"
    index.write_text("content", "utf-8")
    path, info = await _get_fs_info(
        [assets],
        "../index.html",
        fs=file_system,
        allow_symlinks_outside_directory=allow_symlinks_outside_directory,
    )
    assert path is None
    assert info is None


@pytest.mark.parametrize("file_system", (BaseLocalFileSystem(), maybe_wrap_fsspec_file_system(LocalFileSystem())))
@pytest.mark.parametrize("allow_symlinks_outside_directory", (True, False))
async def test_staticfiles_get_fs_info_no_access_to_non_static_file_with_prefix(
    tmp_path: Path,
    file_system: BaseFileSystem,
    allow_symlinks_outside_directory: bool,
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    private_file = tmp_path / "staticsecrets.env"
    private_file.write_text("content", "utf-8")
    path, info = await _get_fs_info(
        [static],
        "../staticsecrets.env",
        fs=file_system,
        allow_symlinks_outside_directory=allow_symlinks_outside_directory,
    )

    assert path is None
    assert info is None
