import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, cast

import pytest

from litestar import HttpMethod, Litestar, MediaType, get
from litestar.exceptions import ImproperlyConfiguredException
from litestar.static_files import StaticFilesConfig, create_static_files_router
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_405_METHOD_NOT_ALLOWED
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.static_files import StaticFiles


@pytest.mark.parametrize("directories", [[], [""]])
@pytest.mark.parametrize("func", [StaticFilesConfig, create_static_files_router])
def test_config_validation_of_directories(func: Any, directories: List[str]) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        func(path="/static", directories=directories)


@pytest.mark.parametrize("func", [StaticFilesConfig, create_static_files_router])
def test_config_validation_of_path(tmpdir: "Path", func: Any) -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    with pytest.raises(ImproperlyConfiguredException):
        func(path="", directories=[tmpdir])

    with pytest.raises(ImproperlyConfiguredException):
        func(path="/{param:int}", directories=[tmpdir])


@pytest.mark.parametrize("func", [StaticFilesConfig, create_static_files_router])
def test_config_validation_of_file_system(tmpdir: "Path", func: Any) -> None:
    class FSWithoutOpen:
        def info(self) -> None:
            return

    with pytest.raises(ImproperlyConfiguredException):
        func(path="/static", directories=[tmpdir], file_system=FSWithoutOpen())

    class FSWithoutInfo:
        def open(self) -> None:
            return

    with pytest.raises(ImproperlyConfiguredException):
        func(path="/static", directories=[tmpdir], file_system=FSWithoutInfo())

    class ImplementedFS:
        def info(self) -> None:
            return

        def open(self) -> None:
            return

    assert func(path="/static", directories=[tmpdir], file_system=ImplementedFS())


def test_runtime_validation_of_static_path_and_path_parameter(tmpdir: "Path") -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    @get("/static/{f:str}", media_type=MediaType.TEXT)
    def handler(f: str) -> str:
        return f

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(
            route_handlers=[handler], static_files_config=[StaticFilesConfig(path="/static", directories=[tmpdir])]
        )


@pytest.mark.parametrize(
    "method, expected",
    (
        (HttpMethod.GET, HTTP_200_OK),
        (HttpMethod.HEAD, HTTP_200_OK),
        (HttpMethod.PUT, HTTP_405_METHOD_NOT_ALLOWED),
        (HttpMethod.PATCH, HTTP_405_METHOD_NOT_ALLOWED),
        (HttpMethod.POST, HTTP_405_METHOD_NOT_ALLOWED),
        (HttpMethod.DELETE, HTTP_405_METHOD_NOT_ALLOWED),
        (HttpMethod.OPTIONS, HTTP_405_METHOD_NOT_ALLOWED),
    ),
)
def test_runtime_validation_of_request_method_legacy_config(tmpdir: "Path", method: HttpMethod, expected: int) -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    with create_test_client(
        [], static_files_config=[StaticFilesConfig(path="/static", directories=[tmpdir])]
    ) as client:
        response = client.request(method, "/static/test.txt")
        assert response.status_code == expected


@pytest.mark.parametrize(
    "method, expected",
    (
        (HttpMethod.GET, HTTP_200_OK),
        (HttpMethod.HEAD, HTTP_200_OK),
        (HttpMethod.OPTIONS, HTTP_204_NO_CONTENT),
        (HttpMethod.PUT, HTTP_405_METHOD_NOT_ALLOWED),
        (HttpMethod.PATCH, HTTP_405_METHOD_NOT_ALLOWED),
        (HttpMethod.POST, HTTP_405_METHOD_NOT_ALLOWED),
        (HttpMethod.DELETE, HTTP_405_METHOD_NOT_ALLOWED),
    ),
)
def test_runtime_validation_of_request_method_create_handler(tmpdir: "Path", method: HttpMethod, expected: int) -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    with create_test_client(create_static_files_router(path="/static", directories=[tmpdir])) as client:
        response = client.request(method, "/static/test.txt")
        assert response.status_code == expected


def test_config_validation_of_path_prevents_directory_traversal(tmpdir: "Path") -> None:
    # Setup: Create a 'secret.txt' outside the static directory to simulate sensitive file
    secret_path = Path(tmpdir) / "../secret.txt"
    secret_path.write_text("This is a secret file.", encoding="utf-8")

    # Setup: Create 'test.txt' inside the static directory
    test_file_path = Path(tmpdir) / "test.txt"
    test_file_path.write_text("This is a test file.", encoding="utf-8")

    # Get StaticFiles handler
    config = StaticFilesConfig(path="/static", directories=[tmpdir])
    asgi_router = config.to_static_files_app()
    static_files_handler = cast("StaticFiles", asgi_router.fn)

    # Resolve file path with the StaticFiles handler
    string_path = Path("../secret.txt").as_posix()

    coroutine = static_files_handler.get_fs_info(directories=static_files_handler.directories, file_path=string_path)
    resolved_path, fs_info = asyncio.run(coroutine)

    assert resolved_path is None  # Because the resolved path is outside the static directory
    assert fs_info is None  # Because the file doesn't exist, so there is no info

    # Resolve file path with the StaticFiles handler
    string_path = Path("test.txt").as_posix()

    coroutine = static_files_handler.get_fs_info(directories=static_files_handler.directories, file_path=string_path)
    resolved_path, fs_info = asyncio.run(coroutine)

    expected_resolved_path = tmpdir / "test.txt"
    assert resolved_path == expected_resolved_path  # Because the resolved path is inside the static directory
    assert fs_info is not None  # Because the file exists, so there is info
