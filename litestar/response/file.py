from __future__ import annotations

from email.utils import formatdate
from inspect import iscoroutine
from mimetypes import encodings_map, guess_type
from typing import TYPE_CHECKING, Any, AsyncGenerator, Coroutine, Literal, cast
from urllib.parse import quote
from zlib import adler32

from litestar.constants import ONE_MEGABYTE
from litestar.exceptions import ImproperlyConfiguredException
from litestar.file_system import BaseLocalFileSystem, FileSystemAdapter
from litestar.response.base import _encode_headers
from litestar.response.streaming import ASGIStreamingResponse, StreamingResponse
from litestar.status_codes import HTTP_200_OK

if TYPE_CHECKING:
    from os import PathLike
    from os import stat_result as stat_result_type

    from anyio import Path

    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.datastructures.headers import ETag
    from litestar.enums import MediaType
    from litestar.types import HTTPResponseBodyEvent, PathType, Receive, ResponseCookies, Send
    from litestar.types.file_types import FileInfo, FileSystemProtocol

__all__ = (
    "ASGIFileResponse",
    "FileResponse",
    "async_file_iterator",
    "create_etag_for_file",
)

# brotli not supported in 'mimetypes.encodings_map' until py 3.9.
encodings_map[".br"] = "br"


async def async_file_iterator(
    file_path: PathType, chunk_size: int, adapter: FileSystemAdapter
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


def create_etag_for_file(path: PathType, modified_time: float, file_size: int) -> str:
    """Create an etag.

    Notes:
        - Function is derived from flask.

    Returns:
        An etag.
    """
    check = adler32(str(path).encode("utf-8")) & 0xFFFFFFFF
    return f'"{modified_time}-{file_size}-{check}"'


class ASGIFileResponse(ASGIStreamingResponse):
    def __init__(
        self,
        file_path: str | PathLike | Path,
        chunk_size: int,
        adapter: FileSystemAdapter,
        etag: ETag | None,
        file_info: FileInfo | Coroutine[None, None, FileInfo],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.adapter = adapter
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.etag = etag
        self.file_info = file_info

    async def send_body(self, send: Send, receive: Receive) -> None:
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
            body_event: HTTPResponseBodyEvent = {
                "type": "http.response.body",
                "body": await file.read(),
                "more_body": False,
            }
            await send(body_event)

    async def start_response(self, send: Send) -> None:
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

        self.content_length = fs_info["size"]
        self.encoded_headers.append((b"content-length", str(self.content_length).encode("ascii")))

        self.encoded_headers.append((b"last-modified", formatdate(fs_info["mtime"], usegmt=True).encode("ascii")))

        if self.etag:
            self.encoded_headers.append((b"etag", self.etag.to_header().encode("ascii")))
        else:
            etag = create_etag_for_file(path=self.file_path, modified_time=fs_info["mtime"], file_size=fs_info["size"])
            self.encoded_headers.append((b"etag", etag.encode("ascii")))

        await super().start_response(send=send)


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
        path: str | PathLike | Path,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        chunk_size: int = ONE_MEGABYTE,
        content_disposition_type: Literal["attachment", "inline"] = "attachment",
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        etag: ETag | None = None,
        file_system: FileSystemProtocol | None = None,
        filename: str | None = None,
        file_info: FileInfo | None = None,
        headers: dict[str, Any] | None = None,
        is_head_response: bool = False,
        media_type: Literal[MediaType.TEXT] | str | None = None,
        stat_result: stat_result_type | None = None,
        status_code: int = HTTP_200_OK,
    ) -> None:
        """Initialize ``FileResponse``

        Notes:
            - This class extends the :class:`StreamingResponse <.response.StreamingResponse>` class.

        Args:
            path: A file path in one of the supported formats.
            status_code: An HTTP status code.
            media_type: A value for the response ``Content-Type`` header. If not provided, the value will be either
                derived from the filename if provided and supported by the stdlib, or will default to
                ``application/octet-stream``.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to None.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: The encoding to be used for the response headers.
            is_head_response: Whether the response should send only the headers ("head" request) or also the content.
            filename: An optional filename to set in the header.
            stat_result: An optional result of calling :func:os.stat:. If not provided, this will be done by the
                response constructor.
            chunk_size: The chunk sizes to use when streaming the file. Defaults to 1MB.
            content_disposition_type: The type of the ``Content-Disposition``. Either ``inline`` or ``attachment``.
            etag: An optional :class:`ETag <.datastructures.ETag>` instance. If not provided, an etag will be
                generated.
            file_system: An implementation of the :class:`FileSystemProtocol <.types.FileSystemProtocol>`. If provided
                it will be used to load the file.
            file_info: The output of calling :meth:`file_system.info <types.FileSystemProtocol.info>`, equivalent to
                providing an :class:`os.stat_result`.
        """
        if not media_type:
            mimetype, content_encoding = guess_type(filename) if filename else (None, None)
            media_type = mimetype or "application/octet-stream"
            if content_encoding is not None:
                headers = headers or {}
                headers.update({"content-encoding": content_encoding})

        self.chunk_size = chunk_size
        self.content_disposition_type = content_disposition_type
        self.etag = etag
        self.file_path = path
        self.filename = filename or ""
        self.adapter = FileSystemAdapter(file_system or BaseLocalFileSystem())

        if file_info:
            self.file_info: FileInfo | Coroutine[Any, Any, FileInfo] = file_info
        elif stat_result:
            self.file_info = self.adapter.parse_stat_result(result=stat_result, path=path)
        else:
            self.file_info = self.adapter.info(self.file_path)

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

    def to_asgi_response(self) -> ASGIFileResponse:
        """Create an ASGIFileResponse from the FileResponse instance.

        Returns:
            An ASGIResponse instance.
        """
        quoted_filename = quote(self.filename)
        is_utf8 = quoted_filename == self.filename
        if is_utf8:
            content_disposition = f'{self.content_disposition_type}; filename="{self.filename}"'
        else:
            content_disposition = f"{self.content_disposition_type}; filename*=utf-8''{quoted_filename}"

        self.headers.pop("content-length", None)
        self.headers.pop("etag", None)
        self.headers.pop("last-modified", None)

        raw_headers = self.raw_headers
        raw_headers.append((b"content-disposition", content_disposition.encode("ascii")))

        return ASGIFileResponse(
            body=b"",
            status_code=self.status_code,
            content_length=0,
            encoded_headers=_encode_headers(headers=self.headers, cookies=self.cookies, raw_headers=self.raw_headers),
            background=self.background,
            is_head_response=self.is_head_response,
            iterator=self.iterator,
            encoding=self.encoding,
            file_path=self.file_path,
            chunk_size=self.chunk_size,
            adapter=self.adapter,
            etag=self.etag,
            file_info=self.file_info,
        )
