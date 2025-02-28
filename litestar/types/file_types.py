from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, TypedDict

__all__ = ("FileInfo", "FileSystemProtocol")


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

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
        start: int | None = None,
        end: int | None = None,
    ) -> bytes: ...

    def iter(self, path: PathType, chunksize: int) -> AsyncGenerator[bytes, None]: ...
