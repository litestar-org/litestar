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
    async def info(self, path: PathType, **kwargs: Any) -> FileInfo: ...

    @abc.abstractmethod
    async def read_bytes(
        self,
        path: PathType,
        start: int = 0,
        end: int = -1,
    ) -> bytes: ...

    @abc.abstractmethod
    def iter(
        self,
        path: PathType,
        chunksize: int,
        start: int = 0,
        end: int = -1,
    ) -> AsyncGenerator[bytes, None]: ...


class LinkableFileSystem(BaseFileSystem, abc.ABC):
    @abc.abstractmethod
    async def resolve_symlinks(self, path: PathType) -> str: ...


AnyFileSystem: TypeAlias = "Union[BaseFileSystem, FsspecFileSystem, FsspecAsyncFileSystem]"
