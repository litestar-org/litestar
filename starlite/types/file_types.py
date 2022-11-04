from typing import Any, Awaitable, Optional, Union

from typing_extensions import Literal, Protocol, TypedDict


class FileInfo(TypedDict):
    created: float
    """Created time stamp, equal to 'stat_result.st_ctime'."""
    destination: Optional[bytes]
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

    def info(self, path: str, **kwargs: Any) -> Union[FileInfo, Awaitable[FileInfo]]:
        """Retrieves information about a given file path.

        Args:
            path: A file path.
            **kwargs: Any additional kwargs.

        Returns:
            A dictionary of file info.
        """
        ...
