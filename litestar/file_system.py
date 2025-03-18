from __future__ import annotations

import pathlib
from stat import S_ISDIR
from typing import TYPE_CHECKING, Any, cast

import anyio

from litestar.concurrency import sync_to_thread
from litestar.plugins import InitPlugin
from litestar.types.file_types import BaseFileSystem, FileSystem

__all__ = (
    "BaseLocalFileSystem",
    "FileSystemPlugin",
    "FsspecAsyncWrapper",
    "FsspecSyncWrapper",
    "maybe_wrap_fsspec_file_system",
    "parse_stat_result",
)


if TYPE_CHECKING:
    import io
    from collections.abc import AsyncGenerator, Mapping
    from os import stat_result

    from fsspec import AbstractFileSystem as FsspecFileSystem
    from fsspec.asyn import AsyncFileSystem as FsspecAsyncFileSystem

    from litestar.types import PathType
    from litestar.types.file_types import FileInfo


class BaseLocalFileSystem(BaseFileSystem):
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
        return await parse_stat_result(path=path, result=result)

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
        return cast("FileInfo", await sync_to_thread(self._fs.info, str(path), **kwargs))

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        return await sync_to_thread(
            self._fs.read_bytes,
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
        fh: io.BytesIO = await sync_to_thread(self._fs.open, str(path), mode="rb")
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
        self._supports_open_async = type(fs).open_async is not FsspecAsyncFileSystem.open_async

        if fs._cat_file is FsspecAsyncFileSystem._cat_file:
            raise TypeError(
                f"Async file system of type {type(fs).__name__!r} does not support "
                "asynchronous reads, as it does not implement an asynchronous _cat "
                "method. To still use this file system asynchronously, explicitly wrap "
                "it in 'FsspecSyncWrapper'"
            )

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        return cast("FileInfo", await self._fs._info(str(path), **kwargs))

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
            async with await self._fs.open_async(path, mode="rb") as fh:
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


async def parse_stat_result(path: PathType, result: stat_result) -> FileInfo:
    """Convert a ``stat_result`` instance into a ``FileInfo``.

    Args:
        path: The file path for which the :func:`stat_result <os.stat_result>` is provided.
        result: The :func:`stat_result <os.stat_result>` instance.

    Returns:
        A dictionary of file info.
    """
    file_info: FileInfo = {
        "created": result.st_ctime,
        "gid": result.st_gid,
        "ino": result.st_ino,
        "islink": await anyio.Path(path).is_symlink(),
        "mode": result.st_mode,
        "mtime": result.st_mtime,
        "name": str(path),
        "nlink": result.st_nlink,
        "size": result.st_size,
        "type": "directory" if S_ISDIR(result.st_mode) else "file",
        "uid": result.st_uid,
    }

    if file_info["islink"]:
        file_info["destination"] = str(await anyio.Path(path).readlink()).encode("utf-8")
        try:
            file_info["size"] = (await anyio.Path(path).stat()).st_size
        except OSError:  # pragma: no cover
            file_info["size"] = result.st_size

    return file_info


def maybe_wrap_fsspec_file_system(file_system: FileSystem) -> BaseFileSystem:
    try:
        from fsspec import AbstractFileSystem
        from fsspec.asyn import AsyncFileSystem
    except ImportError:
        return file_system

    if isinstance(file_system, AsyncFileSystem):
        return FsspecAsyncWrapper(file_system)

    if isinstance(file_system, AbstractFileSystem):
        if file_system.async_impl:
            return FsspecAsyncWrapper(file_system)
        return FsspecSyncWrapper(file_system)

    return file_system


class FileSystemPlugin(InitPlugin):
    def __init__(
        self,
        file_systems: Mapping[str, FileSystem] | None = None,
        default: FileSystem | None = None,
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

    def register(self, scheme: str, fs: FileSystem) -> None:
        self._adapters[scheme] = maybe_wrap_fsspec_file_system(fs)
