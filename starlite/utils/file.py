from stat import S_ISDIR, S_ISLNK
from typing import TYPE_CHECKING, Any, AnyStr, Optional, cast

from anyio import AsyncFile, Path, open_file
from anyio.to_thread import run_sync

from starlite.types.file_types import FileSystemProtocol
from starlite.utils.sync import is_async_callable

if TYPE_CHECKING:
    from os import stat_result

    from _typeshed import OpenBinaryMode

    from starlite.types import PathType
    from starlite.types.file_types import FileInfo


class BaseLocalFileSystem(FileSystemProtocol):
    async def info(self, path: str, **kwargs: Any) -> "FileInfo":  # pylint: disable=W0236
        """Retrieves information about a given file path.

        Args:
            path: A file path.
            **kwargs: Any additional kwargs.

        Returns:
            A dictionary of file info.
        """
        result = await Path(path).stat()
        return await FileSystemAdapter.parse_stat_result(path=path, result=result)

    async def open(  # pylint: disable=invalid-overridden-method
        self,
        file: "PathType",
        mode: str,
        buffering: int = -1,
    ) -> AsyncFile[AnyStr]:
        """Returns a file-like object from the filesystem.

        Notes:
            - The return value must function correctly in a context `with` block.

        Args:
            file: Path to the target file.
            mode: Mode, similar to the built `open`.
            buffering: Buffer size.
        """
        return await open_file(file=file, mode=mode, buffering=buffering)  # type: ignore


class FileSystemAdapter:
    def __init__(self, file_system: "FileSystemProtocol"):
        """This class is a wrapper around a file_system, normalizing
        interaction with it.

        Args:
            file_system: A filesystem class adhering to the [FileSystemProtocol][starlite.types.FileSystemProtocol]
        """
        self.file_system = file_system

    async def info(self, path: "PathType") -> "FileInfo":
        """Proxies the call to the underlying FS Spec's 'info' method, ensuring
        it's done in an async fashion and with strong typing.

        Args:
            path: A file path to load the info for.

        Returns:
            A dictionary of file info.
        """
        awaitable = (
            self.file_system.info(str(path))
            if is_async_callable(self.file_system.info)
            else run_sync(self.file_system.info, str(path))
        )
        return cast("FileInfo", await awaitable)

    async def open(
        self,
        file: "PathType",
        mode: "OpenBinaryMode" = "rb",
        buffering: int = -1,
    ) -> AsyncFile[bytes]:
        """Returns a file-like object from the filesystem.

        Notes:
            - The return value must function correctly in a context `with` block.

        Args:
            file: Path to the target file.
            mode: Mode, similar to the built `open`.
            buffering: Buffer size.
        """
        if is_async_callable(self.file_system.open):  # pyright: ignore
            return cast(
                "AsyncFile[bytes]",
                await self.file_system.open(
                    file=file,
                    mode=mode,
                    buffering=buffering,
                ),
            )
        return AsyncFile(await run_sync(self.file_system.open, file, mode, buffering))  # type: ignore

    @staticmethod
    async def parse_stat_result(path: "PathType", result: "stat_result") -> "FileInfo":
        """Converts a [stat_result][os.stat_result] instance into an.

        [FileInfo][starlite.types.file_types.FileInfo]

        Args:
            path: The file path for which the [stat_result][os.stat_result] is provided.
            result: The [stat_result][os.stat_result] instance.

        Returns:
            A dictionary of file info.
        """
        is_sym_link = S_ISLNK(result.st_mode)
        destination: Optional[bytes] = None
        file_size = result.st_size

        if is_sym_link:
            destination = str(await Path(path).readlink()).encode("utf-8")
            try:
                file_size = (await Path(path).stat(follow_symlinks=True)).st_size
            except OSError:
                file_size = 0

        value_type = "directory" if S_ISDIR(result.st_mode) else "file"

        return {
            "created": result.st_ctime,
            "gid": result.st_gid,
            "ino": result.st_uid,
            "islink": is_sym_link,
            "mode": result.st_mode,
            "mtime": result.st_mtime,
            "name": str(path),
            "nlink": result.st_nlink,
            "size": file_size,
            "type": value_type,  # type: ignore[typeddict-item]
            "uid": result.st_uid,
            "destination": destination,
        }
