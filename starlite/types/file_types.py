from typing import IO, TYPE_CHECKING, Any, AnyStr, Awaitable, Optional, Union, overload

from typing_extensions import Literal, NotRequired, Protocol, TypedDict

if TYPE_CHECKING:
    from _typeshed import OpenBinaryMode, OpenTextMode
    from anyio import AsyncFile

    from starlite.types.composite_types import PathType


class FileInfo(TypedDict):
    created: float
    """Created time stamp, equal to 'stat_result.st_ctime'."""
    destination: NotRequired[Optional[bytes]]
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
    """Base protocol used to interact with a file-system.

    This protocol is commensurable with the file systems
    exported by the [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library.
    """

    def info(self, path: "PathType", **kwargs: Any) -> Union[FileInfo, Awaitable[FileInfo]]:
        """Retrieves information about a given file path.

        Args:
            path: A file path.
            **kwargs: Any additional kwargs.

        Returns:
            A dictionary of file info.
        """
        ...

    @overload
    def open(
        self,
        file: "PathType",
        mode: "OpenBinaryMode",
        buffering: int = -1,
    ) -> Union[IO[bytes], Awaitable["AsyncFile[bytes]"]]:
        """Returns a file-like object from the filesystem.

        Notes:
            - The return value must function correctly in a context `with` block.

        Args:
            file: Path to the target file.
            mode: Mode, similar to the built `open`.
            buffering: Buffer size.
        """
        ...

    @overload
    def open(
        self,
        file: "PathType",
        mode: "OpenTextMode",
        buffering: int = -1,
    ) -> Union[IO[str], Awaitable["AsyncFile[str]"]]:
        """Returns a file-like object from the filesystem.

        Notes:
            - The return value must function correctly in a context `with` block.

        Args:
            file: Path to the target file.
            mode: Mode, similar to the built `open`.
            buffering: Buffer size.
        """
        ...

    def open(  # pyright: ignore
        self,
        file: "PathType",
        mode: str,
        buffering: int = -1,
    ) -> Union[IO[AnyStr], Awaitable["AsyncFile[AnyStr]"]]:
        """Returns a file-like object from the filesystem.

        Notes:
            - The return value must function correctly in a context `with` block.

        Args:
            file: Path to the target file.
            mode: Mode, similar to the built `open`.
            buffering: Buffer size.
        """
        ...
