from __future__ import annotations

import pathlib
from stat import S_ISDIR
from typing import TYPE_CHECKING, Any, cast

import anyio
from fsspec.asyn import AsyncFileSystem as FsspecAsyncFileSystem

from litestar.concurrency import sync_to_thread
from litestar.types.file_types import FileSystemProtocol

__all__ = (
    "BaseLocalFileSystem",
    "ensure_async_file_system",
    "parse_stat_result",
)


if TYPE_CHECKING:
    import io
    from collections.abc import AsyncGenerator
    from os import stat_result

    from fsspec import AbstractFileSystem as FsspecFileSystem

    from litestar.types import PathType
    from litestar.types.file_types import FileInfo


class BaseLocalFileSystem(FileSystemProtocol):
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
        start: int | None = None,
        end: int | None = None,
    ) -> bytes:
        # simple case; read the whole thing in one go
        if start is None and end is None:
            return await sync_to_thread(pathlib.Path(path).read_bytes)

        # we have either a start or end set, so open explicitly and then seek / read
        fh: anyio.AsyncFile
        async with await anyio.open_file(path, mode="rb") as fh:
            if start is not None:
                await fh.seek(start)
            return await fh.read(end or -1)

    async def iter(self, path: PathType, chunksize: int) -> AsyncGenerator[bytes, None]:
        fh: anyio.AsyncFile
        async with await anyio.open_file(path, mode="rb") as fh:
            while chunk := await fh.read(chunksize):
                yield chunk


class FsspecSyncAdapter(FileSystemProtocol):
    def __init__(self, fs: FsspecFileSystem) -> None:
        self._fs = fs

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        return cast("FileInfo", await sync_to_thread(self._fs.info, path, **kwargs))

    async def read_bytes(
        self,
        path: PathType,
        start: int | None = None,
        end: int | None = None,
    ) -> bytes:
        return await sync_to_thread(
            self._fs.read_bytes,
            path,
            start=start,
            end=end,
        )

    async def iter(self, path: PathType, chunksize: int) -> AsyncGenerator[bytes, None]:
        fh: io.BytesIO = await sync_to_thread(self._fs.open, path, mode="rb")
        try:
            while True:
                chunk = await sync_to_thread(fh.read, chunksize)
                yield chunk
                if not chunk:
                    break
        finally:
            fh.close()


class FsspecAsyncAdapter(FileSystemProtocol):
    def __init__(self, fs: FsspecAsyncFileSystem) -> None:
        self._fs = fs
        if fs._cat_file is FsspecAsyncFileSystem._cat_file:
            raise TypeError(
                f"Async file system of type {type(fs).__name__!r} does not support "
                "asynchronous reads, as it does not implement an asynchronous _cat "
                "method. To still use this file system asynchronously, explicitly wrap "
                "it in 'FsspecSyncAdapter'"
            )

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        return cast("FileInfo", await self._fs._info(path, **kwargs))

    async def read_bytes(
        self,
        path: PathType,
        start: int | None = None,
        end: int | None = None,
    ) -> bytes:
        return cast(
            bytes,
            await self._fs._cat_file(path, start=start, end=end),
        )

    async def iter(self, path: PathType, chunksize: int) -> AsyncGenerator[bytes, None]:
        if self._fs.open_async is FsspecAsyncFileSystem.open_async:
            async for chunk in FsspecSyncAdapter(self._fs).iter(path, chunksize):
                yield chunk
            return

        async with self._fs.open_async(path, mode="rb") as fh:
            while chunk := await fh.read(chunksize):
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


def ensure_async_file_system(
    file_system: FileSystemProtocol | FsspecFileSystem | FsspecAsyncFileSystem,
) -> FileSystemProtocol:
    try:
        from fsspec import AbstractFileSystem
        from fsspec.asyn import AsyncFileSystem
    except ImportError:
        return file_system

    if isinstance(file_system, AsyncFileSystem):
        return FsspecAsyncAdapter(file_system)

    if isinstance(file_system, AbstractFileSystem):
        if file_system.async_impl:
            return FsspecAsyncAdapter(file_system)
        return FsspecSyncAdapter(file_system)

    return file_system
