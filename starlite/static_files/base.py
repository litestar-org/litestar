from os.path import commonpath, join
from typing import TYPE_CHECKING, List, Optional, Tuple, Union, cast

from starlite.enums import ScopeType
from starlite.exceptions import (
    InternalServerException,
    MethodNotAllowedException,
    NotAuthorizedException,
    NotFoundException,
)
from starlite.response import FileResponse
from starlite.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from typing import Awaitable, Callable

    from starlite.types import Receive, Scope, Send
    from starlite.types.composite_types import PathType
    from starlite.types.file_types import FileSystemType, FSInfo


class StaticFiles:
    __slots__ = ("html_mode", "directories", "file_info", "file_system")

    def __init__(self, html_mode: bool, directories: List["PathType"], file_system: "FileSystemType"):
        self.html_mode = html_mode
        self.directories = directories
        self.file_system = file_system
        self.file_info = cast("Callable[[str], Awaitable[Optional[FSInfo]]]", AsyncCallable(file_system.info))

    async def get_fs_info(
        self, directories: List["PathType"], file_path: str
    ) -> Union[Tuple[str, "FSInfo"], Tuple[None, None]]:
        """Resolves the file path and returns the resolved path and a.

        [state_result][os.stat_result].

        Args:
            directories: A list of directory paths.
            file_path: A file path to resolve

        Returns:
            A tuple with an optional resolved [Path][anyio.Path] instance and an optional [state_result][os.stat_result].
        """
        for directory in directories:
            try:
                joined_path = join(directory, file_path)  # noqa: PL118
                file_info = await self.file_info(joined_path)
                if file_info and commonpath([str(directory), file_info["name"], joined_path]) == str(directory):
                    return joined_path, file_info
            except FileNotFoundError:
                continue
            except PermissionError as e:
                raise NotAuthorizedException("failed to load file due to missing permissions") from e
            except OSError as e:
                raise InternalServerException from e

        return None, None

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] != ScopeType.HTTP or scope["method"] not in {"GET", "HEAD"}:
            raise MethodNotAllowedException()

        joined_path = join(*scope["path"].split("/"))  # noqa: PL118
        resolved_path, fs_info = await self.get_fs_info(directories=self.directories, file_path=joined_path)

        if fs_info and fs_info["type"] == "directory" and self.html_mode:
            resolved_path, fs_info = await self.get_fs_info(
                directories=self.directories, file_path=join(resolved_path or joined_path, "index.html")
            )

        if fs_info and fs_info["type"] == "file":
            await FileResponse(
                path=resolved_path or joined_path,
                fs_info=fs_info,
                file_system=self.file_system,
                is_head_response=scope["method"] == "HEAD",
                status_code=HTTP_200_OK,
            )(scope, receive, send)
            return

        if self.html_mode:
            resolved_path, fs_info = await self.get_fs_info(directories=self.directories, file_path="404.html")
            if fs_info and fs_info["type"] == "file":
                await FileResponse(
                    path=resolved_path or joined_path,
                    fs_info=fs_info,
                    file_system=self.file_system,
                    is_head_response=scope["method"] == "HEAD",
                    status_code=HTTP_404_NOT_FOUND,
                )(scope, receive, send)
            return

        raise NotFoundException(f"no file or directory match the path {joined_path or joined_path} was found")
