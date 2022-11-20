from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Coroutine,
    Dict,
    Optional,
    Union,
)

from anyio import create_task_group

from starlite.enums import MediaType
from starlite.response.base import Response
from starlite.status_codes import HTTP_200_OK
from starlite.types.composite_types import StreamType
from starlite.utils.sync import AsyncIteratorWrapper

if TYPE_CHECKING:
    from starlite.datastructures import BackgroundTask, BackgroundTasks
    from starlite.enums import OpenAPIMediaType
    from starlite.types import HTTPResponseBodyEvent, Receive, ResponseCookies, Send


class StreamingResponse(Response[StreamType[Union[str, bytes]]]):
    """An HTTP response that streams the response data as a series of ASGI 'http.response.body' events."""

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
        is_head_response: bool = False,
    ):
        """Initialize the response.

        Args:
            content: A sync or async iterator or iterable.
            status_code: An HTTP status code.
            media_type: A value for the response 'Content-Type' header.
            background: A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
                [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
                Defaults to None.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            cookies: A list of [Cookie][starlite.datastructures.Cookie] instances to be set under the response 'Set-Cookie' header.
            encoding: The encoding to be used for the response headers.
            is_head_response: Whether the response should send only the headers ("head" request) or also the content.
        """
        super().__init__(
            background=background,
            content=b"",  # type: ignore[arg-type]
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            media_type=media_type,
            status_code=status_code,
            is_head_response=is_head_response,
        )

        self.iterator: Union[AsyncIterable[Union[str, bytes]], AsyncGenerator[Union[str, bytes], None]] = (
            content if isinstance(content, (AsyncIterable, AsyncIterator)) else AsyncIteratorWrapper(content)
        )

    def create_stream(self, send: "Send") -> Callable[[], Coroutine[None, None, None]]:
        """Create a function that streams the response body.

        Args:
            send: The ASGI Send function.

        Returns:
            A stream function
        """

        async def stream() -> None:
            async for chunk in self.iterator:
                stream_event: "HTTPResponseBodyEvent" = {
                    "type": "http.response.body",
                    "body": chunk if isinstance(chunk, bytes) else chunk.encode(self.encoding),
                    "more_body": True,
                }
                await send(stream_event)

            terminus_event: "HTTPResponseBodyEvent" = {"type": "http.response.body", "body": b"", "more_body": False}
            await send(terminus_event)

        return stream

    async def send_body(self, send: "Send", receive: "Receive") -> None:  # pylint: disable=unused-argument
        """Emit the response body.

        Args:
            send: The ASGI send function.
            receive: The ASGI receive function.

        Notes:
            - Response subclasses should customize this method if there is a need to customize sending data.

        Returns:
            None
        """
        async with create_task_group() as task_group:
            task_group.start_soon(self.create_stream(send=send))
            await self._listen_for_disconnect(cancel_scope=task_group.cancel_scope, receive=receive)
