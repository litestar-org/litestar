from os.path import commonpath, join
from typing import TYPE_CHECKING, Literal, Sequence, Tuple, Union

from starlite.enums import ScopeType
from starlite.exceptions import MethodNotAllowedException, NotFoundException
from starlite.response import FileResponse
from starlite.status_codes import HTTP_404_NOT_FOUND
from starlite.utils.file import FileSystemAdapter

if TYPE_CHECKING:

    from starlite.types import Receive, Scope, Send
    from starlite.types.composite_types import PathType
    from starlite.types.file_types import FileInfo, FileSystemProtocol


class StaticFiles:
    """ASGI App that handles file sending."""

    __slots__ = ("is_html_mode", "directories", "adapter", "send_as_attachment")

    def __init__(
        self,
        is_html_mode: bool,
        directories: Sequence["PathType"],
        file_system: "FileSystemProtocol",
        send_as_attachment: bool = False,
    ) -> None:
        """Initialize the Application.

        Args:
            is_html_mode: Flag dictating whether serving html. If true, the default file will be 'index.html'.
            directories: A list of directories to serve files from.
            file_system: The file_system spec to use for serving files.
            send_as_attachment: Whether to send the file with a `content-disposition` header of
             `attachment` or `inline`
        """
        self.adapter = FileSystemAdapter(file_system)
        self.directories = directories
        self.is_html_mode = is_html_mode
        self.send_as_attachment = send_as_attachment

    async def get_fs_info(
        self, directories: Sequence["PathType"], file_path: str
    ) -> Union[Tuple[str, "FileInfo"], Tuple[None, None]]:
        """Return the resolved path and a [stat_result][os.stat_result].

        Args:
            directories: A list of directory paths.
            file_path: A file path to resolve

        Returns:
            A tuple with an optional resolved [Path][anyio.Path] instance and an optional [stat_result][os.stat_result].
        """
        for directory in directories:
            try:
                joined_path = join(directory, file_path)  # noqa: PL118
                file_info = await self.adapter.info(joined_path)
                if file_info and commonpath([str(directory), file_info["name"], joined_path]) == str(directory):
                    return joined_path, file_info
            except FileNotFoundError:
                continue
        return None, None

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable.

        Args:
            scope: ASGI scope
            receive: ASGI `receive` callable
            send: ASGI `send` callable

        Returns:
            None
        """
        if scope["type"] != ScopeType.HTTP or scope["method"] not in {"GET", "HEAD"}:
            raise MethodNotAllowedException()

        split_path = scope["path"].split("/")
        filename = split_path[-1]
        joined_path = join(*split_path)  # noqa: PL118
        resolved_path, fs_info = await self.get_fs_info(directories=self.directories, file_path=joined_path)
        content_disposition_type: Literal["inline", "attachment"] = (
            "attachment" if self.send_as_attachment else "inline"
        )

        if self.is_html_mode and fs_info and fs_info["type"] == "directory":
            filename = "index.html"
            resolved_path, fs_info = await self.get_fs_info(
                directories=self.directories, file_path=join(resolved_path or joined_path, filename)
            )

        if fs_info and fs_info["type"] == "file":
            await FileResponse(
                path=resolved_path or joined_path,
                file_info=fs_info,
                file_system=self.adapter.file_system,
                filename=filename,
                is_head_response=scope["method"] == "HEAD",
                content_disposition_type=content_disposition_type,
            )(scope, receive, send)
            return

        if self.is_html_mode:
            filename = "404.html"
            resolved_path, fs_info = await self.get_fs_info(directories=self.directories, file_path=filename)
            if fs_info and fs_info["type"] == "file":
                await FileResponse(
                    path=resolved_path or joined_path,
                    file_info=fs_info,
                    file_system=self.adapter.file_system,
                    filename=filename,
                    is_head_response=scope["method"] == "HEAD",
                    status_code=HTTP_404_NOT_FOUND,
                    content_disposition_type=content_disposition_type,
                )(scope, receive, send)
                return

        raise NotFoundException(f"no file or directory match the path {resolved_path or joined_path} was found")
