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

    from starlite.datastructures import BackgroundTask, BackgroundTasks
    from starlite.types import ResponseCookies

ONE_MEGA_BYTE = 1024 * 1024


async def async_file_iterator(file_path: Union[str, "PathLike"], chunk_size: int) -> AsyncGenerator[bytes, None]:
    """
    A generator function that asynchronously reads a file and yields its chunks.
    Args:
        file_path:
        chunk_size:

    Returns:

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
        filename: Optional[str] = None,
        stat_result: Optional["stat_result_type"] = None,
        chunk_size: int = ONE_MEGA_BYTE,
        content_disposition_type: "Literal['attachment', 'inline']" = "attachment",
        etag: Optional[str] = None,
    ) -> None:
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
        return f"{self.stat_result.st_mtime}-{self.stat_result.st_size}-{check}"

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
            Returns the value for the 'Content-Length' header, if applies.
        """
        return self.stat_result.st_size
