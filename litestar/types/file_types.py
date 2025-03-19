from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, TypedDict, Union

from typing_extensions import NotRequired, TypeAlias

__all__ = (
    "AnyFileSystem",
    "BaseFileSystem",
    "FileInfo",
    "LinkableFileSystem",
)


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fsspec import AbstractFileSystem as FsspecFileSystem
    from fsspec.asyn import AsyncFileSystem as FsspecAsyncFileSystem

    from litestar.types.composite_types import PathType


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
        """Return a :class:`~litestar.types.file_types.FileInfo` for the given ``path``"""

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
    @abc.abstractmethod
    async def resolve_symlinks(self, path: PathType) -> str:
        """Return ``path`` with all symlinks resolved"""


AnyFileSystem: TypeAlias = "Union[BaseFileSystem, FsspecFileSystem, FsspecAsyncFileSystem]"
