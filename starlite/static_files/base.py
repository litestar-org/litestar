from os.path import commonpath, join
from typing import TYPE_CHECKING, List, Tuple, Union

from _stat import S_ISDIR, S_ISREG
from anyio import Path
from typing_extensions import Protocol, runtime_checkable

from starlite.enums import ScopeType
from starlite.exceptions import (
    InternalServerException,
    MethodNotAllowedException,
    NotAuthorizedException,
    NotFoundException,
)
from starlite.response import FileResponse
from starlite.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND

if TYPE_CHECKING:
    from os import stat_result

    from starlite.types import Receive, Scope, Send
    from starlite.types.composite import PathType


@runtime_checkable
class StaticFilesBackend(Protocol):
    async def resolve_path(
        self, directories: List["PathType"], file_path: "PathType"
    ) -> Union[Tuple[str, "stat_result"], Tuple[None, None]]:
        """Results a given file path to a file in one of the directories.

        Args:
            directories:
            file_path:

        Returns:
            A two tuple with the full file path and the stat result, or two none values.
        """
        ...


class LocalFilesBackend(StaticFilesBackend):
    async def resolve_path(
        self, directories: List["PathType"], file_path: "PathType"
    ) -> Union[Tuple[str, "stat_result"], Tuple[None, None]]:
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
                resolved_path = await Path.resolve(Path(join(directory, file_path)))
                if commonpath([directory, resolved_path]) != str(directory):
                    continue
                return str(resolved_path), await resolved_path.stat()
            except (FileNotFoundError, NotADirectoryError):
                continue
            except PermissionError as e:
                raise NotAuthorizedException("failed to load file due to missing permissions") from e
            except OSError as e:
                raise InternalServerException from e

        return None, None


class StaticFiles:
    __slots__ = ("html_mode", "directories", "backend")

    def __init__(self, html_mode: bool, directories: List["PathType"], backend: "StaticFilesBackend"):
        self.html_mode = html_mode
        self.directories = directories
        self.backend = backend

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] != ScopeType.HTTP or scope["method"] not in {"GET", "HEAD"}:
            raise MethodNotAllowedException()

        joined_path = join(*scope["path"].split("/"))  # noqa: PL118
        resolved_path, result = await self.backend.resolve_path(directories=self.directories, file_path=joined_path)

        if resolved_path and result and S_ISDIR(result.st_mode) and self.html_mode:
            resolved_path, result = await self.backend.resolve_path(
                directories=self.directories, file_path=join(resolved_path, "index.html")
            )

        if resolved_path and result and S_ISREG(result.st_mode):
            await FileResponse(
                path=resolved_path,
                stat_result=result,
                is_head_response=scope["method"] == "HEAD",
                status_code=HTTP_200_OK,
            )(scope, receive, send)
            return

        if self.html_mode:
            resolved_path, result = await self.backend.resolve_path(
                directories=self.directories, file_path=Path("404.html")
            )
            if resolved_path and result and S_ISREG(result.st_mode):
                await FileResponse(
                    path=resolved_path,
                    stat_result=result,
                    is_head_response=scope["method"] == "HEAD",
                    status_code=HTTP_404_NOT_FOUND,
                )(scope, receive, send)
            return

        raise NotFoundException(f"no file or directory match the path {joined_path} was found")
