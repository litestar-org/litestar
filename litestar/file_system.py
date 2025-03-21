from __future__ import annotations

import abc
import io
import os
import os.path
import pathlib
from datetime import datetime
from stat import S_ISDIR, S_ISLNK
from typing import TYPE_CHECKING, Any, Final, Union, cast

import anyio
from typing_extensions import NotRequired, TypeAlias, TypedDict

from litestar.concurrency import sync_to_thread
from litestar.plugins import InitPlugin

__all__ = (
    "AnyFileSystem",
    "BaseFileSystem",
    "BaseLocalFileSystem",
    "FileInfo",
    "FileSystemRegistry",
    "FsspecAsyncWrapper",
    "FsspecSyncWrapper",
    "LinkableFileSystem",
    "get_fsspec_mtime_equivalent",
    "maybe_wrap_fsspec_file_system",
    "parse_stat_result",
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

    from fsspec import AbstractFileSystem as FsspecFileSystem
    from fsspec.asyn import AsyncFileSystem as FsspecAsyncFileSystem

    from litestar.types import PathType


AnyFileSystem: TypeAlias = "Union[BaseFileSystem, FsspecFileSystem, FsspecAsyncFileSystem]"


class FileInfo(TypedDict):
    """File information gathered from a file system."""

    islink: bool
    """True if the file is a symbolic link."""
    mtime: NotRequired[float]
    """Modified time stamp."""
    name: str
    """The path of the file."""
    size: int
    """Total size, in bytes."""
    type: str
    """The type of the file system object."""


class BaseFileSystem(abc.ABC):
    @abc.abstractmethod
    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        """Return a :class:`~litestar.file_system.FileInfo` for the given ``path``"""

    @abc.abstractmethod
    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        """Read bytes from ``path``

        Args:
            path: File to read from
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """

    @abc.abstractmethod
    def iter(
        self,
        path: PathType,
        chunksize: int,
        start: int = 0,
        end: int = -1,
    ) -> AsyncGenerator[bytes, None]:
        """Stream bytes from ``path``

        Args:
            path: Path to read from
            chunksize: Number of bytes to read per chunk
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """


class LinkableFileSystem(BaseFileSystem, abc.ABC):
    """A file system that supports symlinks"""

    @abc.abstractmethod
    async def resolve_symlinks(self, path: PathType) -> str:
        """Return ``path`` with all symlinks resolved"""


class BaseLocalFileSystem(LinkableFileSystem):
    """Base class for a local file system."""

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        """Return a :class:`~litestar.file_system.FileInfo` for the given ``path``"""
        result = await sync_to_thread(pathlib.Path(path).stat)
        return parse_stat_result(path=path, result=result)

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        """Read bytes from ``path``

        Args:
            path: File to read from
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """
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
        """Stream bytes from ``path``

        Args:
            path: Path to read from
            chunksize: Number of bytes to read per chunk
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """

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

    async def resolve_symlinks(self, path: PathType) -> str:
        return os.path.realpath(path)


class FsspecSyncWrapper(BaseFileSystem):
    def __init__(self, fs: FsspecFileSystem) -> None:
        """Wrap a :class:`fsspec.spec.AbstractFileSystem` to provide a
        :class:`litestar.file_system.BaseFileSystem` compatible interface
        """
        self._fs = fs

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        """Return a :class:`~litestar.file_system.FileInfo` for the given ``path``.

        Return info verbatim from :meth:`fsspec.spec.AbstractFileSystem.info`, but try to
        patch 'mtime' using :func:`litestar.file_system.get_fsspec_mtime_equivalent`.
        """
        result = await sync_to_thread(self._fs.info, str(path), **kwargs)
        result["mtime"] = get_fsspec_mtime_equivalent(result)
        return cast("FileInfo", result)

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        """Read bytes from ``path`` using :meth:`fsspec.spec.AbstractFileSystem.cat_file`

        Args:
            path: File to read from
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """
        return await sync_to_thread(
            self._fs.cat_file,  # pyright: ignore
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
        """Stream bytes from ``path`` using :meth:`fsspec.spec.AbstractFileSystem.open`

        Args:
            path: Path to read from
            chunksize: Number of bytes to read per chunk
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """

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
        """Wrap a :class:`fsspec.asyn.AsyncFileSystem` to provide a
        class:`litestar.file_system.BaseFileSystem` compatible interface

        Args:
            fs: An :class:`fsspec.asyn.AsyncFileSystem` instantiated with `
                `asynchronous=True``
        """
        import fsspec.asyn

        self._fs = fs
        # 'open_async' may not be implemented
        self._supports_open_async = type(fs).open_async is not fsspec.asyn.AsyncFileSystem.open_async

    async def info(self, path: PathType, **kwargs: Any) -> FileInfo:
        """Return a :class:`~litestar.file_system.FileInfo` for the given ``path``.

        Return info verbatim from ``fsspec.async.AsyncFileSystem._info``, but try
        to patch 'mtime' using :func:`litestar.file_system.get_fsspec_mtime_equivalent`.
        """
        result = await self._fs._info(str(path), **kwargs)
        result["mtime"] = get_fsspec_mtime_equivalent(result)
        return cast("FileInfo", result)

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes:
        """Read bytes from ``path`` using ``fsspec.asyn.AsyncFileSystem._cat_file``

        Args:
            path: File to read from
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """
        return cast(
            bytes,
            await self._fs._cat_file(
                str(path),
                start=start or None,
                end=end if end != -1 else None,
            ),
        )

    async def iter(self, path: PathType, chunksize: int, start: int = 0, end: int = -1) -> AsyncGenerator[bytes, None]:
        """Stream bytes from ``path``.

        If no offsets are given and the file system implements
        ``fsspec.async.AsyncFileSystem.async_open``, use ``async_open``, otherwise read
        chunks manually using ``fsspec.async.AsyncFileSystem._cat_file``

        Args:
            path: Path to read from
            chunksize: Number of bytes to read per chunk
            start: Offset to start reading from
            end: Offset to stop reading at (inclusive)
        """

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


def parse_stat_result(path: PathType, result: os.stat_result) -> FileInfo:
    """Convert a ``stat_result`` instance into a ``FileInfo``.

    Args:
        path: The file path for which the :class:`~os.stat_result` is provided
        result: The :class:`~os.stat_result` instance

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
    """If ``file_system`` is an fsspec file system, wrap it in
    :class:`~litestar.file_system.FsspecSyncWrapper` or
    :class:`~litestar.file_system.FsspecAsyncWrapper` depending on its type. If fsspec
    is not installed or ``file_system`` is not an fsspec file system, return
    ``file_system``
    """
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
        """File system registry

        Args:
            file_systems: A mapping of names to file systems
            default: Default file system to use when no system is specified. If
                ``None``, default to :class:`~litestar.file_system.BaseLocalFileSystem`
        """
        self._adapters: dict[str, BaseFileSystem] = {}
        self.register("file", BaseLocalFileSystem())
        if file_systems:
            for scheme, fs in file_systems.items():
                self.register(scheme, fs)

        if default is not None:
            self._default = maybe_wrap_fsspec_file_system(default)
        else:
            self._default = BaseLocalFileSystem()

    @property
    def default(self) -> BaseFileSystem:
        """Return the default file system"""
        return self._default

    def __getitem__(self, name: str) -> BaseFileSystem:
        return self._adapters[name]

    def get(self, name: str) -> BaseFileSystem | None:
        """Return the file system registered under ``name``. If no matching file system is
        found, return ``None``
        """
        return self._adapters.get(name)

    def register(self, name: str, fs: AnyFileSystem) -> None:
        """Register a file system ``fs`` under ``name``. If a file system was previously
        registered under this name, it will be overwritten
        """
        self._adapters[name] = maybe_wrap_fsspec_file_system(fs)


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
