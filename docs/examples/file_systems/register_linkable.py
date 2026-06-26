import os

from fsspec.implementations.local import LocalFileSystem

from litestar.file_system import AnyFileSystem, LinkableFileSystem
from litestar.types import PathType


async def local_resolver(fs: AnyFileSystem, path: PathType) -> str:
    return os.path.realpath(path)


# Register LocalFileSystem as supporting symlinks
LinkableFileSystem.register_as_linkable(LocalFileSystem, local_resolver)
