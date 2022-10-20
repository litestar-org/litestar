from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Dict,
    Optional,
    Union,
)

from starlite.enums import MediaType
from starlite.response.base import Response
from starlite.status_codes import HTTP_200_OK
from starlite.types.composite import StreamType
from starlite.utils.sync import iterate_sync_iterator

if TYPE_CHECKING:
    from starlite.datastructures import BackgroundTask, BackgroundTasks
    from starlite.enums import OpenAPIMediaType
    from starlite.types import (
        HTTPResponseBodyEvent,
        Receive,
        ResponseCookies,
        Scope,
        Send,
    )


class StreamingResponse(Response[StreamType[Union[str, bytes]]]):
    __slots__ = ("iterator",)

    def __init__(
        self,
        content: StreamType[Union[str, bytes]],
        *,
        status_code: int = HTTP_200_OK,
        media_type: Union[MediaType, "OpenAPIMediaType", str] = MediaType.JSON,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cookies: Optional["ResponseCookies"] = None,
        encoding: str = "utf-8",
    ):
        super().__init__(
            background=background,
            content=b"",  # type: ignore[arg-type]
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            media_type=media_type,
            status_code=status_code,
        )
        self.iterator: Union[AsyncIterable[Union[str, bytes]], AsyncGenerator[Union[str, bytes], None]] = (
            content if isinstance(content, (AsyncIterable, AsyncIterator)) else iterate_sync_iterator(content)
        )

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        await self.start_response(send=send)

        async for chunk in self.iterator:
            stream_event: "HTTPResponseBodyEvent" = {
                "type": "http.response.body",
                "body": chunk if isinstance(chunk, bytes) else chunk.encode(self.encoding),
                "more_body": True,
            }
            await send(stream_event)

        terminus_event: "HTTPResponseBodyEvent" = {"type": "http.response.body", "body": b"", "more_body": False}
        await send(terminus_event)

        await self.after_response()
