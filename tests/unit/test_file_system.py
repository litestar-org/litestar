import os
import pathlib
import threading
from collections.abc import AsyncGenerator, Generator
from http.server import HTTPServer
from typing import Any

import aiohttp
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from RangeHTTPServer import RangeRequestHandler  # type: ignore[import-untyped]

from litestar.file_system import (
    BaseFileSystem,
    BaseLocalFileSystem,
    FileSystemRegistry,
    FsspecAsyncWrapper,
    FsspecSyncWrapper,
    maybe_wrap_fsspec_file_system,
)
from litestar.testing.client.subprocess_client import _get_available_port


class PatchedHTTPFileSystem(HTTPFileSystem):  # type: ignore[misc]
    async def _cat_file(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return await super()._cat_file(*args, **kwargs)
        except aiohttp.ClientResponseError as exc:
            # this is an implementation specific error case; we expect most file systems
            # to return an empty byte-string when trying to read beyond the limits of
            # the file
            if exc.status == 416:
                return b""
            raise exc


@pytest.fixture(scope="session")
def tmp_dir(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    return tmp_path_factory.mktemp("test")


@pytest.fixture(scope="session")
def http_server_port() -> int:
    return _get_available_port()


@pytest.fixture
def file() -> pathlib.Path:
    return pathlib.Path("test.txt")


@pytest.fixture()
def local_fs(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> BaseLocalFileSystem:
    monkeypatch.chdir(tmp_path)
    file = tmp_path / "test.txt"
    file.write_bytes(b"0123456789")
    return BaseLocalFileSystem()


@pytest.fixture()
def fsspec_local_fs(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> BaseFileSystem:
    monkeypatch.chdir(tmp_path)
    file = tmp_path / "test.txt"
    file.write_bytes(b"0123456789")
    return FsspecSyncWrapper(LocalFileSystem())


@pytest.fixture(scope="session")
def http_server(tmp_dir: pathlib.Path, http_server_port: int) -> Generator[None, None, None]:
    current_dir = os.getcwd()
    os.chdir(tmp_dir)

    file = tmp_dir / "test.txt"
    file.write_bytes(b"0123456789")

    server = HTTPServer(("127.0.0.1", http_server_port), RangeRequestHandler)  # pyright: ignore
    thread = threading.Thread(daemon=True, target=server.serve_forever)
    thread.start()
    try:
        yield
    finally:
        server.server_close()
        server.shutdown()
        thread.join()
        os.chdir(current_dir)


@pytest.fixture()
async def http_fs(
    tmp_path: pathlib.Path, http_server: None, http_server_port: int
) -> AsyncGenerator[BaseFileSystem, None]:
    client = aiohttp.ClientSession(f"http://127.0.0.1:{http_server_port}")

    async def get_client(**kwargs: Any) -> aiohttp.ClientSession:
        return client

    fs = PatchedHTTPFileSystem(get_client=get_client, asynchronous=True)
    yield FsspecAsyncWrapper(fs)
    await client.close()


@pytest.fixture(
    params=[
        "local_fs",
        "fsspec_local_fs",
        # there's a bug in the fs with handling the aiohttp session that can cause a warning
        # to be emitted due to improper resource closing. we can't really handle this here
        pytest.param("http_fs", marks=[pytest.mark.flaky(reruns=10)]),
    ]
)
def fs(request: pytest.FixtureRequest) -> BaseFileSystem:
    return request.getfixturevalue(request.param)  # type: ignore[no-any-return]


async def test_read_bytes(fs: BaseFileSystem, file: pathlib.Path) -> None:
    content = await fs.read_bytes(file)
    assert content == file.read_bytes()


async def test_read_bytes_offset(fs: BaseFileSystem, file: pathlib.Path) -> None:
    content = await fs.read_bytes(file, start=1)
    assert content == file.read_bytes()[1:]


async def test_read_bytes_end(fs: BaseFileSystem, file: pathlib.Path) -> None:
    content = await fs.read_bytes(file, end=4)
    assert content == file.read_bytes()[:4]


async def test_read_bytes_start_end(fs: BaseFileSystem, file: pathlib.Path) -> None:
    content = await fs.read_bytes(file, start=1, end=5)
    assert content == file.read_bytes()[1:5]


@pytest.mark.parametrize("chunksize", [1, 5, 100])
async def test_read_iter(fs: BaseFileSystem, file: pathlib.Path, chunksize: int) -> None:
    content = b"".join([c async for c in fs.iter(file, chunksize=chunksize)])
    assert content == file.read_bytes()


@pytest.mark.parametrize("chunksize", [1, 5, 100])
async def test_iter_offset(fs: BaseFileSystem, file: pathlib.Path, chunksize: int) -> None:
    content = b"".join([c async for c in fs.iter(file, chunksize=chunksize, start=1)])
    assert content == file.read_bytes()[1:]


@pytest.mark.parametrize("chunksize", [1, 5, 100])
async def test_iter_end(fs: BaseFileSystem, file: pathlib.Path, chunksize: int) -> None:
    content = b"".join([c async for c in fs.iter(file, chunksize=chunksize, end=4)])
    assert content == file.read_bytes()[:4]


@pytest.mark.parametrize("chunksize", [1, 5, 100])
async def test_iter_start_end(fs: BaseFileSystem, file: pathlib.Path, chunksize: int) -> None:
    content = b"".join([c async for c in fs.iter(file, chunksize=chunksize, start=1, end=5)])
    assert content == file.read_bytes()[1:5]


def test_registry_get() -> None:
    fs = BaseLocalFileSystem()
    registry = FileSystemRegistry({"my_fs": fs})
    assert registry.get("my_fs") is fs
    assert registry.get("something") is None
    assert registry["my_fs"] is fs
    with pytest.raises(KeyError):
        registry["something"]


def test_registry_default() -> None:
    fs = BaseLocalFileSystem()
    registry = FileSystemRegistry(default=fs)
    assert registry.default is fs

    assert isinstance(FileSystemRegistry().default, BaseLocalFileSystem)


@pytest.mark.parametrize(
    "fs, expected_fs",
    [
        (BaseLocalFileSystem(), BaseLocalFileSystem),
        (LocalFileSystem(), FsspecSyncWrapper),
        (HTTPFileSystem(), FsspecAsyncWrapper),
    ],
)
def test_maybe_wrap_fsspec_file_system(fs: Any, expected_fs: type[BaseFileSystem]) -> None:
    assert isinstance(maybe_wrap_fsspec_file_system(fs), expected_fs)
