from email.utils import formatdate
from mimetypes import guess_type
from stat import S_ISREG
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Optional, Union, cast
from urllib.parse import quote
from zlib import adler32

from anyio import Path, open_file

from starlite.enums import MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.response.streaming import StreamingResponse
from starlite.status_codes import HTTP_200_OK
from starlite.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from os import PathLike
    from os import stat_result as stat_result_type
    from typing import Awaitable, Callable

    from typing_extensions import Literal

    from starlite.datastructures import BackgroundTask, BackgroundTasks, ETag
    from starlite.types import PathType, ResponseCookies, Send
    from starlite.types.file_types import FileSystemType, FSInfo

ONE_MEGA_BYTE: int = 1024 * 1024


async def async_file_iterator(file_path: "PathType", chunk_size: int) -> AsyncGenerator[bytes, None]:
    """
    A generator function that asynchronously reads a file and yields its chunks.
    Args:
        file_path: A path to a file.
        chunk_size: The chunk file to use.

    Returns:
        An async generator.
    """
    async with await open_file(file_path, mode="rb") as file:
        yield await file.read(chunk_size)


def create_etag_for_file(path: "PathType", modified_time: float, file_size: int) -> str:
    """Creates an etag.

    Notes:
        - Function is derived from flask.

    Returns:
        An etag.
    """
    check = adler32(str(path).encode("utf-8")) & 0xFFFFFFFF
    return f'"{modified_time}-{file_size}-{check}"'


class FileResponse(StreamingResponse):
    __slots__ = (
        "stat_result",
        "filename",
        "chunk_size",
        "file_path",
        "file_system",
        "fs_info",
        "content_disposition_type",
        "filename",
        "etag",
    )

    def __init__(
        self,
        path: Union[str, "PathLike", "Path"],
        *,
        status_code: int = HTTP_200_OK,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        chunk_size: int = ONE_MEGA_BYTE,
        content_disposition_type: "Literal['attachment', 'inline']" = "attachment",
        cookies: Optional["ResponseCookies"] = None,
        encoding: str = "utf-8",
        etag: Optional["ETag"] = None,
        file_system: Optional["FileSystemType"] = None,
        filename: Optional[str] = None,
        fs_info: Optional["FSInfo"] = None,
        headers: Optional[Dict[str, Any]] = None,
        is_head_response: bool = False,
        media_type: Optional[Union["Literal[MediaType.TEXT]", str]] = None,
        stat_result: Optional["stat_result_type"] = None,
    ) -> None:
        """This class allows streaming a file as response body.

        Notes:
            - This class extends the [StreamingReesponse][starlite.response.StreamingResponse] class.

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
            file_system: An fsspec filesystem implementation. If provided it will be used to load the file.
            fs_info: The output of calling fsspec file_system.info(..), equivalent to providing a stat_result.
        """
        if not media_type:
            mimetype, _ = guess_type(filename) if filename else (None, None)
            media_type = mimetype or "application/octet-stream"

        super().__init__(
            content=async_file_iterator(file_path=path, chunk_size=chunk_size),
            status_code=status_code,
            media_type=media_type,
            background=background,
            headers=headers,
            cookies=cookies,
            encoding=encoding,
            is_head_response=is_head_response,
        )
        self.file_path = path
        self.file_system = file_system
        self.fs_info = fs_info
        self.stat_result = stat_result
        self.content_disposition_type = content_disposition_type
        self.filename = filename or ""
        self.etag = etag

    @property
    def content_disposition(self) -> str:
        """

        Returns:
            A value for the 'Content-Disposition' header.
        """
        quoted_filename = quote(self.filename)
        is_utf8 = quoted_filename == self.filename
        if is_utf8:
            return f'{self.content_disposition_type}; filename="{self.filename}"'
        return f"{self.content_disposition_type}; filename*=utf-8''{quoted_filename}"

    @property
    def content_length(self) -> Optional[int]:
        """

        Returns:
            Returns the value of 'self.stat_result.st_size' to populate the 'Content-Length' header.
        """
        if self.stat_result:
            return self.stat_result.st_size
        if self.fs_info:
            return self.fs_info["size"]
        return 0

    async def start_response(self, send: "Send") -> None:

        if self.file_system and not self.fs_info:
            get_file_info = cast("Callable[[str], Awaitable[Optional[FSInfo]]]", AsyncCallable(self.file_system.info))
            self.fs_info = await get_file_info(str(self.file_path))
            if not self.fs_info:
                raise ImproperlyConfiguredException(f"{self.file_path} doesn't exist")
        elif not self.fs_info and not self.stat_result:
            try:
                self.stat_result = await Path(self.file_path).stat()
            except FileNotFoundError as e:
                raise ImproperlyConfiguredException(f"{self.file_path} doesn't exist") from e

        if self.fs_info and self.fs_info["type"] == "file":
            modified_time = self.fs_info["mtime"]
            file_size = self.fs_info["size"]
        elif self.stat_result and S_ISREG(self.stat_result.st_mode):
            stat_result = cast("stat_result_type", self.stat_result)
            modified_time = stat_result.st_mtime
            file_size = stat_result.st_size
        else:
            raise ImproperlyConfiguredException(f"{self.file_path} is not a file")

        self.set_header("last-modified", formatdate(modified_time, usegmt=True))
        self.set_header("content-disposition", self.content_disposition)
        self.set_etag(
            self.etag or create_etag_for_file(path=self.file_path, modified_time=modified_time, file_size=file_size)
        )

        await super().start_response(send=send)
