from email.utils import formatdate
from mimetypes import guess_type
from os.path import basename
from pathlib import Path
from stat import S_ISREG
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Optional, Union, cast
from urllib.parse import quote
from zlib import adler32

from anyio import open_file

from starlite.enums import MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.response.streaming import StreamingResponse
from starlite.status_codes import HTTP_200_OK

if TYPE_CHECKING:

    from os import PathLike
    from os import stat_result as stat_result_type

    from typing_extensions import Literal

    from starlite.datastructures import BackgroundTask, BackgroundTasks, ETag
    from starlite.types import ResponseCookies

ONE_MEGA_BYTE: int = 1024 * 1024


async def async_file_iterator(file_path: Union[str, "PathLike", Path], chunk_size: int) -> AsyncGenerator[bytes, None]:
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


class FileResponse(StreamingResponse):
    __slots__ = ("stat_result", "filename", "chunk_size")

    def __init__(
        self,
        path: Union[str, "PathLike", "Path"],
        *,
        status_code: int = HTTP_200_OK,
        media_type: Optional[Union["Literal[MediaType.TEXT]", str]] = None,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cookies: Optional["ResponseCookies"] = None,
        encoding: str = "utf-8",
        is_head_response: bool = False,
        filename: Optional[str] = None,
        stat_result: Optional["stat_result_type"] = None,
        chunk_size: int = ONE_MEGA_BYTE,
        content_disposition_type: "Literal['attachment', 'inline']" = "attachment",
        etag: Optional["ETag"] = None,
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
        self.stat_result = cast("stat_result_type", self._get_stat_result(path=path, stat_result=stat_result))
        self.set_header("last-modified", formatdate(self.stat_result.st_mtime, usegmt=True))
        self.set_header(
            "content-disposition",
            self._get_content_disposition(
                filename=filename or basename(path), content_disposition_type=content_disposition_type
            ),
        )
        self.set_etag(etag or self._create_etag(path=path))

    def _create_etag(self, path: Union[str, "PathLike"]) -> str:
        """Creates an etag.

        Notes:
            - Function is derived from flask.

        Returns:
            An etag.
        """
        check = adler32(str(path).encode("utf-8")) & 0xFFFFFFFF
        return f'"{self.stat_result.st_mtime}-{self.stat_result.st_size}-{check}"'

    @staticmethod
    def _get_stat_result(path: Union[str, "PathLike"], stat_result: Optional["stat_result_type"]) -> "stat_result_type":
        """

        Args:
            stat_result: An optional [stat_result][os.stat_result] instance.

        Returns:
            An [stat_result][os.stat_result] instance.
        """
        try:
            if stat_result is None:
                stat_result = Path(path).stat()
            if not S_ISREG(stat_result.st_mode):
                raise ImproperlyConfiguredException(f"{path} is not a file")
            return stat_result
        except FileNotFoundError as e:
            raise ImproperlyConfiguredException(f"file {path} doesn't exist") from e

    @staticmethod
    def _get_content_disposition(filename: str, content_disposition_type: "Literal['attachment', 'inline']") -> str:
        """

        Args:
            content_disposition_type: The Content-Disposition type of the file.

        Returns:
            A value for the 'Content-Disposition' header.
        """
        quoted_filename = quote(filename)
        is_utf8 = quoted_filename == filename
        if is_utf8:
            return f'{content_disposition_type}; filename="{filename}"'
        return f"{content_disposition_type}; filename*=utf-8''{quoted_filename}"

    @property
    def content_length(self) -> Optional[int]:
        """

        Returns:
            Returns the value of 'self.stat_result.st_size' to populate the 'Content-Length' header.
        """
        return self.stat_result.st_size
