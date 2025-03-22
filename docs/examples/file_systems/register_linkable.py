import os

from fsspec.implementations.local import LocalFileSystem

from litestar.file_system import AnyFileSystem, LinkableFileSystem


async def local_resolver(fs: AnyFileSystem, path: str) -> str:
    return os.path.realpath(path)


# Register LocalFileSystem as supporting symlinks
LinkableFileSystem.register_as_linkable(LocalFileSystem, local_resolver)
