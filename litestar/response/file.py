from __future__ import annotations

import itertools
from datetime import datetime
from email.utils import formatdate
from mimetypes import encodings_map, guess_type
from os import stat_result as stat_result_type
from typing import TYPE_CHECKING, Any, Final, Literal, cast
from urllib.parse import quote
from zlib import adler32

from litestar.constants import ONE_MEGABYTE
from litestar.exceptions import ImproperlyConfiguredException
from litestar.file_system import (
    FileSystemPlugin,
    maybe_wrap_fsspec_file_system,
    parse_stat_result,
)
from litestar.response.base import Response
from litestar.response.streaming import ASGIStreamingResponse
from litestar.utils.helpers import get_enum_string_value

if TYPE_CHECKING:
    from collections.abc import Iterable
    from os import PathLike

    from anyio import Path
    from fsspec import AbstractFileSystem
    from fsspec.asyn import AsyncFileSystem as AbstractAsyncFileSystem

    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.datastructures.cookie import Cookie
    from litestar.datastructures.headers import ETag
    from litestar.enums import MediaType
    from litestar.types import (
        HTTPResponseBodyEvent,
        PathType,
        Receive,
        ResponseCookies,
        ResponseHeaders,
        Send,
        TypeEncodersMap,
    )
    from litestar.types.file_types import FileInfo, FileSystemProtocol

__all__ = (
    "ASGIFileResponse",
    "File",
    "create_etag_for_file",
)

# brotli not supported in 'mimetypes.encodings_map' until py 3.9.
encodings_map[".br"] = "br"


def create_etag_for_file(path: PathType, modified_time: float | None, file_size: int) -> str:
    """Create an etag.

    Notes:
        - Function is derived from flask.

    Returns:
        An etag.
    """
    check = adler32(str(path).encode("utf-8")) & 0xFFFFFFFF
    parts = [str(file_size), str(check)]
    if modified_time:
        parts.insert(0, str(modified_time))
    return f'"{"-".join(parts)}"'


_MTIME_KEYS: Final = (
    "mtime",
    "ctime",
    "Last-Modified",
    "updated_at",
    "modification_time",
    "last_changed",
    "change_time",
    "last_modified",
    "last_updated",
    "timestamp",
)


def get_fsspec_mtime_equivalent(info: dict[str, Any]) -> float | None:
    """Return the 'mtime' or equivalent for different fsspec implementations, since they
    are not standardized.

    See https://github.com/fsspec/filesystem_spec/issues/526.
    """
    # inspired by https://github.com/mdshw5/pyfaidx/blob/cac82f24e9c4e334cf87a92e477b92d4615d260f/pyfaidx/__init__.py#L1318-L1345
    mtime: Any | None = next((info[key] for key in _MTIME_KEYS if key in info), None)
    if mtime is None or isinstance(mtime, float):
        return mtime
    if isinstance(mtime, datetime):
        return mtime.timestamp()
    if isinstance(mtime, str):
        return datetime.fromisoformat(mtime.replace("Z", "+00:00")).timestamp()

    raise ValueError(f"Unsupported mtime-type value type {type(mtime)!r}")


class ASGIFileResponse(ASGIStreamingResponse):
    """A low-level ASGI response, streaming a file as response body."""

    def __init__(
        self,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        chunk_size: int = ONE_MEGABYTE,
        content_disposition_type: Literal["attachment", "inline"] = "attachment",
        content_length: int | None = None,
        cookies: Iterable[Cookie] | None = None,
        encoded_headers: Iterable[tuple[bytes, bytes]] | None = None,
        encoding: str = "utf-8",
        etag: ETag | None = None,
        file_info: FileInfo | stat_result_type | None = None,
        file_path: str | PathLike | Path,
        file_system: FileSystemProtocol,
        filename: str = "",
        headers: dict[str, str] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
    ) -> None:
        """A low-level ASGI response, streaming a file as response body.

        Args:
            background: A background task or a list of background tasks to be executed after the response is sent.
            chunk_size: The chunk size to use.
            content_disposition_type: The type of the ``Content-Disposition``. Either ``inline`` or ``attachment``.
            content_length: The response content length.
            cookies: The response cookies.
            encoded_headers: A list of encoded headers.
            encoding: The response encoding.
            etag: An etag.
            file_info: A file info.
            file_path: A path to a file.
            file_system: A file system adapter.
            filename: The name of the file.
            headers: A dictionary of headers.
            headers: The response headers.
            is_head_response: A boolean indicating if the response is a HEAD response.
            media_type: The media type of the file.
            status_code: The response status code.
        """
        headers = headers or {}
        if not media_type:
            mimetype, content_encoding = guess_type(filename) if filename else (None, None)
            media_type = mimetype or "application/octet-stream"
            if content_encoding is not None:
                headers.update({"content-encoding": content_encoding})

        self._file_system = file_system

        super().__init__(
            iterator=iter(b""),
            headers=headers,
            media_type=media_type,
            cookies=cookies,
            background=background,
            status_code=status_code,
            content_length=content_length,
            encoding=encoding,
            is_head_response=is_head_response,
            encoded_headers=encoded_headers,
        )

        quoted_filename = quote(filename)
        is_utf8 = quoted_filename == filename
        if is_utf8:
            content_disposition = f'{content_disposition_type}; filename="{filename}"'
        else:
            content_disposition = f"{content_disposition_type}; filename*=utf-8''{quoted_filename}"

        self.headers.setdefault("content-disposition", content_disposition)

        self.chunk_size = chunk_size
        self.etag = etag
        self.file_path = file_path
        self.file_info = file_info

    async def send_body(self, send: Send, receive: Receive) -> None:
        """Emit a stream of events correlating with the response body.

        Args:
            send: The ASGI send function.
            receive: The ASGI receive function.

        Returns:
            None
        """
        if self.content_length < self.chunk_size:
            # no need to chunk and stream; read and send the whole thing in one go
            body_event: HTTPResponseBodyEvent = {
                "type": "http.response.body",
                "body": await self._file_system.read_bytes(self.file_path),
                "more_body": False,
            }
            await send(body_event)

        else:
            self.iterator = self._file_system.iter(self.file_path, chunksize=self.chunk_size)
            await super().send_body(send=send, receive=receive)

    async def start_response(self, send: Send) -> None:
        """Emit the start event of the response. This event includes the headers and status codes.

        Args:
            send: The ASGI send function.

        Returns:
            None
        """

        try:
            if self.file_info is None:
                file_info = cast("FileInfo", await self._file_system.info(self.file_path))
            elif isinstance(self.file_info, stat_result_type):
                file_info = await parse_stat_result(self.file_path, self.file_info)
            else:
                file_info = self.file_info
        except FileNotFoundError as e:
            raise ImproperlyConfiguredException(f"{self.file_path} does not exist") from e

        if file_info["type"] != "file":
            raise ImproperlyConfiguredException(f"{self.file_path} is not a file")

        self.content_length = file_info["size"]

        self.headers.setdefault("content-length", str(self.content_length))
        mtime = get_fsspec_mtime_equivalent(file_info)

        if mtime is not None:
            self.headers.setdefault("last-modified", formatdate(mtime, usegmt=True))

        if self.etag:
            self.headers.setdefault("etag", self.etag.to_header())
        else:
            self.headers.setdefault(
                "etag",
                create_etag_for_file(
                    path=self.file_path,
                    modified_time=mtime,
                    file_size=file_info["size"],
                ),
            )

        await super().start_response(send=send)


class File(Response):
    """A response, streaming a file as response body."""

    __slots__ = (
        "chunk_size",
        "content_disposition_type",
        "etag",
        "file_info",
        "file_path",
        "file_system",
        "filename",
        "stat_result",
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
        file_info: FileInfo | stat_result_type | None = None,
        file_system: str | FileSystemProtocol | AbstractFileSystem | AbstractAsyncFileSystem | None = None,
        filename: str | None = None,
        headers: ResponseHeaders | None = None,
        media_type: Literal[MediaType.TEXT] | str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize ``File``

        Notes:
            - This class extends the :class:`Stream <.response.Stream>` class.

        Args:
            path: A file path in one of the supported formats.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to None.
            chunk_size: The chunk sizes to use when streaming the file. Defaults to 1MB.
            content_disposition_type: The type of the ``Content-Disposition``. Either ``inline`` or ``attachment``.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: The encoding to be used for the response headers.
            etag: An optional :class:`ETag <.datastructures.ETag>` instance. If not provided, an etag will be
                generated.
            file_info: The output of calling :meth:`file_system.info <types.FileSystemProtocol.info>`, equivalent to
                providing an :class:`os.stat_result`.
            file_system: An implementation of the :class:`FileSystemProtocol <.types.FileSystemProtocol>`. If provided
                it will be used to load the file.
            filename: An optional filename to set in the header.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            media_type: A value for the response ``Content-Type`` header. If not provided, the value will be either
                derived from the filename if provided and supported by the stdlib, or will default to
                ``application/octet-stream``.
            status_code: An HTTP status code.
        """

        self.chunk_size = chunk_size
        self.content_disposition_type = content_disposition_type
        self.etag = etag
        self.file_info = file_info
        self.file_path = path
        self.file_system = file_system
        self.filename = filename or ""

        super().__init__(
            content=None,
            status_code=status_code,
            media_type=media_type,
            background=background,
            headers=headers,
            cookies=cookies,
            encoding=encoding,
        )

    def to_asgi_response(
        self,
        request: Request,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        encoded_headers: Iterable[tuple[bytes, bytes]] | None = None,
        cookies: Iterable[Cookie] | None = None,
        headers: dict[str, str] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
        type_encoders: TypeEncodersMap | None = None,
    ) -> ASGIFileResponse:
        """Create an :class:`ASGIFileResponse <litestar.response.file.ASGIFileResponse>` instance.

        Args:
            background: Background task(s) to be executed after the response is sent.
            cookies: A list of cookies to be set on the response.
            encoded_headers: A list of already encoded headers.
            headers: Additional headers to be merged with the response headers. Response headers take precedence.
            is_head_response: Whether the response is a HEAD response.
            media_type: Media type for the response. If ``media_type`` is already set on the response, this is ignored.
            request: The :class:`Request <.connection.Request>` instance.
            status_code: Status code for the response. If ``status_code`` is already set on the response, this is
            type_encoders: A dictionary of type encoders to use for encoding the response content.

        Returns:
            A low-level ASGI file response.
        """

        headers = {**headers, **self.headers} if headers is not None else self.headers
        cookies = self.cookies if cookies is None else itertools.chain(self.cookies, cookies)

        media_type = self.media_type or media_type
        if media_type is not None:
            media_type = get_enum_string_value(media_type)

        file_system: FileSystemProtocol
        if self.file_system is None:
            file_system = request.app.plugins.get(FileSystemPlugin).default
        elif isinstance(self.file_system, str):
            file_system_plugin = request.app.plugins.get(FileSystemPlugin)
            file_system = file_system_plugin[self.file_system]
        else:
            file_system = maybe_wrap_fsspec_file_system(self.file_system)

        return ASGIFileResponse(
            file_path=self.file_path,
            file_system=file_system,
            filename=self.filename,
            background=self.background or background,
            chunk_size=self.chunk_size,
            content_disposition_type=self.content_disposition_type,  # pyright: ignore
            content_length=0,
            cookies=cookies,
            encoded_headers=encoded_headers,
            encoding=self.encoding,
            etag=self.etag,
            file_info=self.file_info,
            headers=headers,
            is_head_response=is_head_response,
            media_type=media_type,
            status_code=self.status_code or status_code,
        )
