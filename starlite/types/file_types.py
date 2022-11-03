from typing import Any, Awaitable, Dict, Optional, Union

from typing_extensions import Literal, Protocol, TypedDict


class FSInfo(TypedDict):
    created: float
    gid: int
    ino: int
    islink: bool
    mode: int
    mtime: float
    name: str
    nlink: int
    size: int
    type: Literal["file", "directory", "other"]
    uid: int
    destination: Optional[bytes]


class FileSystemProtocol(Protocol):
    def info(self, path: str, **kwargs: Any) -> Union[Dict[str, Any], Awaitable[Dict[str, Any]]]:
        """Retrieves information about a given file path.

        Args:
            path: A file path.
            **kwargs: Any additional kwargs.

        Returns:
            A dictionary of file info.
        """
        ...
