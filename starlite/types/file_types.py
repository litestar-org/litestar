from typing import Optional, Union

from fsspec import AbstractFileSystem
from fsspec.asyn import AsyncFileSystem
from typing_extensions import Literal, TypedDict


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


FileSystemType = Union["AbstractFileSystem", "AsyncFileSystem"]
