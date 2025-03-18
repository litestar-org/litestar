from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, TypedDict, Union

from typing_extensions import TypeAlias

__all__ = (
    "FileInfo",
    "FileSystem",
    "FileSystemProtocol",
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fsspec import AbstractFileSystem as FsspecFileSystem
    from fsspec.asyn import AsyncFileSystem as FsspecAsyncFileSystem
    from typing_extensions import NotRequired

    from litestar.types.composite_types import PathType


class FileInfo(TypedDict):
    """File information gathered from a file system."""

    created: float
    """Created time stamp, equal to 'stat_result.st_ctime'."""
    destination: NotRequired[bytes | None]
    """Output of loading a symbolic link."""
    gid: int
    """Group ID of owner."""
    ino: int
    """inode value."""
    islink: bool
    """True if the file is a symbolic link."""
    mode: int
    """Protection mode."""
    mtime: float
    """Modified time stamp."""
    name: str
    """The path of the file."""
    nlink: int
    """Number of hard links."""
    size: int
    """Total size, in bytes."""
    type: Literal["file", "directory", "other"]
    """The type of the file system object."""
    uid: int
    """User ID of owner."""


class FileSystemProtocol(Protocol):
    async def info(self, path: PathType, **kwargs: Any) -> FileInfo: ...

    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes: ...

    def iter(
        self,
        path: PathType,
        chunksize: int,
        start: int = 0,
        end: int = -1,
    ) -> AsyncGenerator[bytes, None]: ...


FileSystem: TypeAlias = "Union[FileSystemProtocol, FsspecFileSystem, FsspecAsyncFileSystem]"
