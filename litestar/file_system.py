from __future__ import annotations

import io
import os.path
import pathlib
from datetime import datetime
from stat import S_ISDIR, S_ISLNK
from typing import TYPE_CHECKING, Any, Final, cast

import anyio

from litestar.concurrency import sync_to_thread
from litestar.plugins import InitPlugin
from litestar.types.file_types import AnyFileSystem, BaseFileSystem, LinkableFileSystem

__all__ = (
    "BaseLocalFileSystem",
    "FileSystemRegistry",
    "FsspecAsyncWrapper",
    "FsspecSyncWrapper",
    "get_fsspec_mtime_equivalent",
    "maybe_wrap_fsspec_file_system",
    "parse_stat_result",
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping
    from os import stat_result

    from fsspec import AbstractFileSystem as FsspecFileSystem
    from fsspec.asyn import AsyncFileSystem as FsspecAsyncFileSystem

    from litestar.types import PathType
    from litestar.types.file_types import FileInfo


class BaseLocalFileSystem(LinkableFileSystem):
    """Base class for a local file system."""

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        """Retrieve information about a given file path.

        Args:
            path: A file path.
            **kwargs: Any additional kwargs.

        Returns:
            A dictionary of file info.
        """
        result = await sync_to_thread(pathlib.Path(path).stat)
        return parse_stat_result(path=path, result=result)

    async def resolve_symlinks(self, path: PathType) -> str:
        return os.path.realpath(path)

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        # simple case; read the whole thing in one go
        if start == 0 and end == -1:
            return await sync_to_thread(pathlib.Path(path).read_bytes)

        # we have either a start or end set, so open explicitly and then seek / read
        fh: anyio.AsyncFile
        if end != -1:
            end = end - start
        async with await anyio.open_file(path, mode="rb") as fh:
            if start:
                await fh.seek(start)
            return await fh.read(end)

    async def iter(
        self,
        path: PathType,
        chunksize: int,
        start: int = 0,
        end: int = -1,
    ) -> AsyncGenerator[bytes, None]:
        fh: anyio.AsyncFile
        async with await anyio.open_file(path, mode="rb") as fh:
            if start != 0:
                await fh.seek(start)

            current_pos = start
            while True:
                to_read = chunksize
                if end != -1:
                    if current_pos >= end:
                        break

                    to_read = min(chunksize, end - current_pos)

                chunk = await fh.read(to_read)

                if not chunk:
                    break

                yield chunk

                current_pos = await fh.tell()


class FsspecSyncWrapper(BaseFileSystem):
    def __init__(self, fs: FsspecFileSystem) -> None:
        self._fs = fs

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        result = await sync_to_thread(self._fs.info, str(path), **kwargs)
        result["mtime"] = get_fsspec_mtime_equivalent(result)
        return cast("FileInfo", result)

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        return await sync_to_thread(
            self._fs.read_bytes,  # pyright: ignore
            str(path),
            start=start or None,
            end=end if end != -1 else None,
        )

    async def iter(
        self,
        path: PathType,
        chunksize: int,
        start: int = 0,
        end: int = -1,
    ) -> AsyncGenerator[bytes, None]:
        fh = cast(io.BytesIO, await sync_to_thread(self._fs.open, str(path), mode="rb"))
        try:
            if start != 0:
                await sync_to_thread(fh.seek, start)

            to_read = chunksize
            while True:
                if end != -1:
                    current_pos = await sync_to_thread(fh.tell)
                    if current_pos >= end:
                        break

                    to_read = min(chunksize, end - current_pos)

                chunk = await sync_to_thread(fh.read, to_read)

                if not chunk:
                    break

                yield chunk
        finally:
            await sync_to_thread(fh.close)


class FsspecAsyncWrapper(BaseFileSystem):
    def __init__(self, fs: FsspecAsyncFileSystem) -> None:
        from fsspec.asyn import AsyncFileSystem as FsspecAsyncFileSystem

        self._fs = fs
        # 'open_async' may not be implemented
        self._supports_open_async = type(fs).open_async is not FsspecAsyncFileSystem.open_async

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        result = await self._fs._info(str(path), **kwargs)
        result["mtime"] = get_fsspec_mtime_equivalent(result)
        return cast("FileInfo", result)

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        return cast(
            bytes,
            await self._fs._cat_file(
                str(path),
                start=start or None,
                end=end if end != -1 else None,
            ),
        )

    async def iter(self, path: PathType, chunksize: int, start: int = 0, end: int = -1) -> AsyncGenerator[bytes, None]:
        path = str(path)

        # if we want to stream the whole thing we can use '.open_async' if it's
        # implemented
        if start == 0 and end == -1 and self._supports_open_async:
            async with await self._fs.open_async(path, mode="rb") as fh:  # pyright: ignore
                while chunk := await fh.read(chunksize):
                    yield chunk
            return

        # if 'open_async' is not implemented, or 'start' or 'end' are set, we have to do
        # a bit more work.
        # the object returned by open_async()' does not support seek + tell or other
        # mechanisms for reading specific ranges
        # https://github.com/fsspec/filesystem_spec/issues/1772
        to_read = chunksize
        current_pos = start
        while True:
            if end != -1:
                if current_pos >= end:
                    break

                to_read = min(chunksize, end - current_pos)

            chunk = await self.read_bytes(path, start=current_pos, end=current_pos + to_read)

            if not chunk:
                break

            current_pos += len(chunk)

            yield chunk


def parse_stat_result(path: PathType, result: stat_result) -> FileInfo:
    """Convert a ``stat_result`` instance into a ``FileInfo``.

    Args:
        path: The file path for which the :func:`stat_result <os.stat_result>` is provided.
        result: The :func:`stat_result <os.stat_result>` instance.

    Returns:
        A dictionary of file info.
    """
    return {
        "islink": S_ISLNK(result.st_mode),
        "mtime": result.st_mtime,
        "name": str(path),
        "size": result.st_size,
        "type": "directory" if S_ISDIR(result.st_mode) else "file",
    }


def maybe_wrap_fsspec_file_system(file_system: AnyFileSystem) -> BaseFileSystem:
    try:
        from fsspec import AbstractFileSystem
        from fsspec.asyn import AsyncFileSystem
    except ImportError:
        return cast(BaseFileSystem, file_system)

    if isinstance(file_system, AsyncFileSystem):
        return FsspecAsyncWrapper(file_system)

    if isinstance(file_system, AbstractFileSystem):
        return FsspecSyncWrapper(file_system)

    return file_system


class FileSystemRegistry(InitPlugin):
    def __init__(
        self,
        file_systems: Mapping[str, AnyFileSystem] | None = None,
        default: AnyFileSystem | None = None,
    ) -> None:
        self._adapters: dict[str, BaseFileSystem] = {}
        self.register("file", BaseLocalFileSystem())
        if file_systems:
            for scheme, fs in file_systems.items():
                self.register(scheme, fs)

        if default is not None:
            self.default = maybe_wrap_fsspec_file_system(default)
        else:
            self.default = BaseLocalFileSystem()

    def __getitem__(self, name: str) -> BaseFileSystem:
        return self._adapters[name]

    def get(self, name: str) -> BaseFileSystem | None:
        return self._adapters.get(name)

    def register(self, scheme: str, fs: AnyFileSystem) -> None:
        self._adapters[scheme] = maybe_wrap_fsspec_file_system(fs)


_MTIME_KEYS: Final = (
    "mtime",
    "ctime",
    "Last-Modified",
    "updated_at",
    "modification_time",
    "last_changed",
    "change_time",
    "last_modified",
    "last_updated",
    "timestamp",
)


def get_fsspec_mtime_equivalent(info: dict[str, Any]) -> float | None:
    """Return the 'mtime' or equivalent for different fsspec implementations, since they
    are not standardized.

    See https://github.com/fsspec/filesystem_spec/issues/526.
    """
    # inspired by https://github.com/mdshw5/pyfaidx/blob/cac82f24e9c4e334cf87a92e477b92d4615d260f/pyfaidx/__init__.py#L1318-L1345
    mtime: Any | None = next((info[key] for key in _MTIME_KEYS if key in info), None)
    if mtime is None or isinstance(mtime, float):
        return mtime
    if isinstance(mtime, datetime):
        return mtime.timestamp()
    if isinstance(mtime, str):
        return datetime.fromisoformat(mtime.replace("Z", "+00:00")).timestamp()

    raise ValueError(f"Unsupported mtime-type value type {type(mtime)!r}")
