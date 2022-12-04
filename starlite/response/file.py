from email.utils import formatdate
from inspect import iscoroutine
from mimetypes import guess_type
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Coroutine,
    Dict,
    Literal,
    Optional,
    Union,
    cast,
)
from urllib.parse import quote
from zlib import adler32

from starlite.constants import ONE_MEGABYTE
from starlite.enums import MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.response.streaming import StreamingResponse
from starlite.status_codes import HTTP_200_OK
from starlite.utils.file import BaseLocalFileSystem, FileSystemAdapter

if TYPE_CHECKING:
    from os import PathLike
    from os import stat_result as stat_result_type

    from anyio import Path

    from starlite.datastructures import BackgroundTask, BackgroundTasks, ETag
    from starlite.types import (
        HTTPResponseBodyEvent,
        PathType,
        Receive,
        ResponseCookies,
        Send,
    )
    from starlite.types.file_types import FileInfo, FileSystemProtocol


async def async_file_iterator(
    file_path: "PathType", chunk_size: int, adapter: "FileSystemAdapter"
) -> AsyncGenerator[bytes, None]:
    """Return an async that asynchronously reads a file and yields its chunks.

    Args:
        file_path: A path to a file.
        chunk_size: The chunk file to use.
        adapter: File system adapter class.
        adapter: File system adapter class.

    Returns:
        An async generator.
    """
    async with await adapter.open(file_path) as file:
        while chunk := await file.read(chunk_size):
            yield chunk


def create_etag_for_file(path: "PathType", modified_time: float, file_size: int) -> str:
    """Create an etag.

    Notes:
        - Function is derived from flask.

    Returns:
        An etag.
    """
    check = adler32(str(path).encode("utf-8")) & 0xFFFFFFFF
    return f'"{modified_time}-{file_size}-{check}"'


class FileResponse(StreamingResponse):
    """A response, streaming a file as response body."""

    __slots__ = (
        "chunk_size",
        "content_disposition_type",
        "etag",
        "file_path",
        "filename",
        "adapter",
        "file_info",
    )

    def __init__(
        self,
        path: Union[str, "PathLike", "Path"],
        *,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        chunk_size: int = ONE_MEGABYTE,
        content_disposition_type: Literal["attachment", "inline"] = "attachment",
        cookies: Optional["ResponseCookies"] = None,
        encoding: str = "utf-8",
        etag: Optional["ETag"] = None,
        file_system: Optional["FileSystemProtocol"] = None,
        filename: Optional[str] = None,
        file_info: Optional["FileInfo"] = None,
        headers: Optional[Dict[str, Any]] = None,
        is_head_response: bool = False,
        media_type: Optional[Union[Literal[MediaType.TEXT], str]] = None,
        stat_result: Optional["stat_result_type"] = None,
        status_code: int = HTTP_200_OK,
    ) -> None:
        """Initialize `FileResponse`

        Notes:
            - This class extends the [StreamingResponse][starlite.response.StreamingResponse] class.

        Args:
            path: A file path in one of the supported formats.
            status_code: An HTTP status code.
            media_type: A value for the response 'Content-Type' header. If not provided, the value will be either
                derived from the filename if provided and supported by the stdlib, or will default to
                'application/octet-stream'.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of [Cookie][starlite.datastructures.Cookie] instances to be set under the response 'Set-Cookie' header.
            encoding: The encoding to be used for the response headers.
            is_head_response: Whether the response should send only the headers ("head" request) or also the content.
            filename: An optional filename to set in the header.
            stat_result: An optional result of calling 'os.stat'. If not provided, this will be done by the response
                constructor.
            chunk_size: The chunk sizes to use when streaming the file. Defaults to 1MB.
            content_disposition_type: The type of the 'Content-Disposition'. Either 'inline' or 'attachment'.
            etag: An optional [ETag][starlite.datastructures.ETag] instance.
                If not provided, an etag will be automatically generated.
            file_system: An implementation of the [`FileSystemProtocol][starlite.types.FileSystemProtocol]. If provided
                it will be used to load the file.
            file_info: The output of calling `file_system.info(..)`, equivalent to providing a `stat_result`.
        """
        if not media_type:
            mimetype, _ = guess_type(filename) if filename else (None, None)
            media_type = mimetype or "application/octet-stream"

        self.chunk_size = chunk_size
        self.content_disposition_type = content_disposition_type
        self.etag = etag
        self.file_path = path
        self.filename = filename or ""
        self.adapter = FileSystemAdapter(file_system or BaseLocalFileSystem())

        super().__init__(
            content=async_file_iterator(file_path=path, chunk_size=chunk_size, adapter=self.adapter),
            status_code=status_code,
            media_type=media_type,
            background=background,
            headers=headers,
            cookies=cookies,
            encoding=encoding,
            is_head_response=is_head_response,
        )

        if file_info:
            self.file_info: Union["FileInfo", "Coroutine[Any, Any, 'FileInfo']"] = file_info
        elif stat_result:
            self.file_info = self.adapter.parse_stat_result(result=stat_result, path=path)
        else:
            self.file_info = self.adapter.info(self.file_path)

    @property
    def content_disposition(self) -> str:
        """Content disposition.

        Returns:
            A value for the 'Content-Disposition' header.
        """
        quoted_filename = quote(self.filename)
        is_utf8 = quoted_filename == self.filename
        if is_utf8:
            return f'{self.content_disposition_type}; filename="{self.filename}"'
        return f"{self.content_disposition_type}; filename*=utf-8''{quoted_filename}"

    @property
    def content_length(self) -> int:
        """Content length of the response if applicable.

        Returns:
            Returns the value of 'self.stat_result.st_size' to populate the 'Content-Length' header.
        """
        if isinstance(self.file_info, dict):
            return self.file_info["size"]
        return 0

    async def send_body(self, send: "Send", receive: "Receive") -> None:
        """Emit a stream of events correlating with the response body.

        Args:
            send: The ASGI send function.
            receive: The ASGI receive function.

        Returns:
            None
        """
        if self.chunk_size < self.content_length:
            await super().send_body(send=send, receive=receive)
            return

        async with await self.adapter.open(self.file_path) as file:
            body_event: "HTTPResponseBodyEvent" = {
                "type": "http.response.body",
                "body": await file.read(),
                "more_body": False,
            }
            await send(body_event)

    async def start_response(self, send: "Send") -> None:
        """Emit the start event of the response. This event includes the headers and status codes.

        Args:
            send: The ASGI send function.

        Returns:
            None
        """
        try:
            fs_info = self.file_info = cast(
                "FileInfo", (await self.file_info if iscoroutine(self.file_info) else self.file_info)
            )
        except FileNotFoundError as e:
            raise ImproperlyConfiguredException(f"{self.file_path} does not exist") from e

        if fs_info["type"] != "file":
            raise ImproperlyConfiguredException(f"{self.file_path} is not a file")

        self.set_header("last-modified", formatdate(fs_info["mtime"], usegmt=True))
        self.set_header("content-disposition", self.content_disposition)
        self.set_etag(
            self.etag
            or create_etag_for_file(path=self.file_path, modified_time=fs_info["mtime"], file_size=fs_info["size"])
        )

        await super().start_response(send=send)
