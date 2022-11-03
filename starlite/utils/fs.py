from stat import S_ISDIR, S_ISLNK
from typing import TYPE_CHECKING, Optional, cast

from anyio import Path
from anyio.to_thread import run_sync

from starlite.types import PathType
from starlite.utils.sync import is_async_callable

if TYPE_CHECKING:
    from os import stat_result

    from starlite.types.file_types import FileSystemType, FSInfo


class FileSystemAdapter:
    def __init__(self, fs: "FileSystemType"):
        self.fs = fs

    async def info(self, path: "PathType") -> "FSInfo":
        """Proxies the call to the underlying FS Spec's 'info' method, ensuring
        it's done in an async fashion and with strong typing.

        Args:
            path: A file path to load the info for.

        Returns:
            A dictionary of file info.
        """
        awaitable = self.fs.info(path) if is_async_callable(self.fs.info) else run_sync(self.fs.info, path)
        return cast("FSInfo", await awaitable)

    @staticmethod
    async def parse_stat_result(path: "PathType", result: "stat_result") -> "FSInfo":
        """Converts a [stat_result][os.stat_result] instance into an.

        [FSInfo][starlite.types.file_types.FSInfo]

        Args:
            path: The file path for which the [stat_result][os.stat_result] is provided.
            result: The [stat_result][os.stat_result] instance

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
            "name": str(PathType),
            "nlink": result.st_nlink,
            "size": file_size,
            "type": value_type,  # type: ignore[typeddict-item]
            "uid": result.st_uid,
            "destination": destination,
        }
