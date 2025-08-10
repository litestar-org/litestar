from __future__ import annotations

import io
import itertools
import re
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, AsyncGenerator, AsyncIterable, AsyncIterator, Callable, Iterable, Iterator

from anyio import Event, create_task_group, sleep

from litestar.concurrency import sync_to_thread
from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.streaming import ASGIStreamingResponse, Stream
from litestar.utils import AsyncIteratorWrapper
from litestar.utils.deprecation import warn_deprecation
from litestar.utils.helpers import get_enum_string_value

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.datastructures.cookie import Cookie
    from litestar.enums import OpenAPIMediaType
    from litestar.response.base import ASGIResponse
    from litestar.types import (
        HTTPResponseBodyEvent,
        Receive,
        ResponseCookies,
        ResponseHeaders,
        Send,
        SSEData,
        StreamType,
        TypeEncodersMap,
    )

_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")
DEFAULT_SEPARATOR = "\r\n"


class _ServerSentEventIterator(AsyncIteratorWrapper[bytes]):
    __slots__ = ("comment_message", "content_async_iterator", "event_id", "event_type", "retry_duration")

    content_async_iterator: AsyncIterable[SSEData]

    def __init__(
        self,
        content: str | bytes | StreamType[SSEData],
        event_type: str | None = None,
        event_id: int | str | None = None,
        retry_duration: int | None = None,
        comment_message: str | None = None,
    ) -> None:
        self.comment_message = comment_message
        self.event_id = event_id
        self.event_type = event_type
        self.retry_duration = retry_duration
        chunks: list[bytes] = []
        if comment_message is not None:
            chunks.extend([f": {chunk}\r\n".encode() for chunk in _LINE_BREAK_RE.split(comment_message)])

        if event_id is not None:
            chunks.append(f"id: {event_id}\r\n".encode())

        if event_type is not None:
            chunks.append(f"event: {event_type}\r\n".encode())

        if retry_duration is not None:
            chunks.append(f"retry: {retry_duration}\r\n".encode())

        super().__init__(iterator=chunks)

        if not isinstance(content, (Iterator, AsyncIterator, AsyncIteratorWrapper)) and callable(content):
            content = content()  # type: ignore[unreachable]

        if isinstance(content, (str, bytes)):
            self.content_async_iterator = AsyncIteratorWrapper([content])
        elif isinstance(content, (Iterable, Iterator)):
            self.content_async_iterator = AsyncIteratorWrapper(content)
        elif isinstance(content, (AsyncIterable, AsyncIterator, AsyncIteratorWrapper)):
            self.content_async_iterator = content
        else:
            raise ImproperlyConfiguredException(f"Invalid type {type(content)} for ServerSentEvent")

    def ensure_bytes(self, data: str | int | bytes | dict | ServerSentEventMessage | Any, sep: str) -> bytes:
        if isinstance(data, ServerSentEventMessage):
            return data.encode()
        if isinstance(data, dict):
            data["sep"] = sep
            return ServerSentEventMessage(**data).encode()

        return ServerSentEventMessage(
            data=data, id=self.event_id, event=self.event_type, retry=self.retry_duration, sep=sep
        ).encode()

    def _call_next(self) -> bytes:
        try:
            return next(self.iterator)
        except StopIteration as e:
            raise ValueError from e

    async def _async_generator(self) -> AsyncGenerator[bytes, None]:
        while True:
            try:
                yield await sync_to_thread(self._call_next)
            except ValueError:
                async for value in self.content_async_iterator:
                    yield self.ensure_bytes(value, DEFAULT_SEPARATOR)
                break


@dataclass
class ServerSentEventMessage:
    data: str | int | bytes | None = ""
    event: str | None = None
    id: int | str | None = None
    retry: int | None = None
    comment: str | None = None
    sep: str = DEFAULT_SEPARATOR

    def encode(self) -> bytes:
        buffer = io.StringIO()
        if self.comment is not None:
            for chunk in _LINE_BREAK_RE.split(str(self.comment)):
                buffer.write(f": {chunk}")
                buffer.write(self.sep)

        if self.id is not None:
            buffer.write(_LINE_BREAK_RE.sub("", f"id: {self.id}"))
            buffer.write(self.sep)

        if self.event is not None:
            buffer.write(_LINE_BREAK_RE.sub("", f"event: {self.event}"))
            buffer.write(self.sep)

        if self.data is not None:
            data = self.data
            for chunk in _LINE_BREAK_RE.split(data.decode() if isinstance(data, bytes) else str(data)):
                buffer.write(f"data: {chunk}")
                buffer.write(self.sep)

        if self.retry is not None:
            buffer.write(f"retry: {self.retry}")
            buffer.write(self.sep)

        buffer.write(self.sep)
        return buffer.getvalue().encode("utf-8")


class ASGIStreamingSSEResponse(ASGIStreamingResponse):
    """A streaming response which support sending ping messages specific for SSE."""

    __slots__ = (
        "is_content_end",
        "ping_interval",
    )

    def __init__(
        self,
        *,
        iterator: StreamType,
        background: BackgroundTask | BackgroundTasks | None = None,
        body: bytes | str = b"",
        content_length: int | None = None,
        cookies: Iterable[Cookie] | None = None,
        encoded_headers: Iterable[tuple[bytes, bytes]] | None = None,
        encoding: str = "utf-8",
        headers: dict[str, Any] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
        ping_interval: float = 0,
    ) -> None:
        """A SSE ASGI streaming response.

        Args:
            background: A background task or a list of background tasks to be executed after the response is sent.
            body: encoded content to send in the response body.
                .. deprecated:: 2.16
            content_length: The response content length.
            cookies: The response cookies.
            encoded_headers: The response headers.
            encoding: The response encoding.
            headers: The response headers.
            is_head_response: A boolean indicating if the response is a HEAD response.
            iterator: An async iterator or iterable.
            media_type: The response media type.
            status_code: The response status code.
            ping_interval: The interval in seconds between "ping" messages.
            is_content_end: Indicates the ending of content in the iterator, e.g., use to stop sending ping events.
        """
        super().__init__(
            iterator=iterator,
            background=background,
            body=body,
            content_length=content_length,
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            is_head_response=is_head_response,
            media_type=media_type,
            status_code=status_code,
            encoded_headers=encoded_headers,
        )
        self.ping_interval = ping_interval
        self.is_content_end = Event()

    async def _send_ping_event(self, send: Send) -> None:
        """Send ping events every `ping_interval` second.

        Args:
            send: The ASGI Send function.

        Returns:
            None
        """
        if not self.ping_interval:
            return

        ping_event: HTTPResponseBodyEvent = {
            "type": "http.response.body",
            "body": b"event: ping\r\n\r\n",
            "more_body": True,
        }

        while not self.is_content_end.is_set():
            await send(ping_event)
            await sleep(self.ping_interval)

    async def _stream(self, send: Send) -> None:
        """Send the chunks from the iterator as a stream of ASGI 'http.response.body' events.

        Args:
            send: The ASGI Send function.

        Returns:
            None
        """
        async for chunk in self.iterator:
            stream_event: HTTPResponseBodyEvent = {
                "type": "http.response.body",
                "body": chunk if isinstance(chunk, bytes) else chunk.encode(self.encoding),
                "more_body": True,
            }
            await send(stream_event)
        terminus_event: HTTPResponseBodyEvent = {"type": "http.response.body", "body": b"", "more_body": False}
        self.is_content_end.set()
        await send(terminus_event)

    async def send_body(self, send: Send, receive: Receive) -> None:
        """Emit a stream of events correlating with the response body.

        Args:
            send: The ASGI send function.
            receive: The ASGI receive function.

        Returns:
            None
        """

        async with create_task_group() as task_group:
            task_group.start_soon(partial(self._stream, send))
            task_group.start_soon(partial(self._send_ping_event, send))
            await self._listen_for_disconnect(cancel_scope=task_group.cancel_scope, receive=receive)


class SSEStream(Stream):
    """An HTTP response that streams the response data as a series of ASGI ``http.response.body`` events."""

    __slots__ = ("ping_interval",)

    def __init__(
        self,
        content: StreamType[str | bytes] | Callable[[], StreamType[str | bytes]],
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        headers: ResponseHeaders | None = None,
        media_type: MediaType | OpenAPIMediaType | str | None = None,
        status_code: int | None = None,
        ping_interval: float = 0,
    ) -> None:
        """Initialize the response.

        Args:
            content: A sync or async iterator or iterable.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to None.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: The encoding to be used for the response headers.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            media_type: A value for the response ``Content-Type`` header.
            status_code: An HTTP status code.
            ping_interval: The interval in seconds between "ping" messages.
        """
        super().__init__(
            background=background,
            content=b"",  # type: ignore[arg-type]
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            media_type=media_type,
            status_code=status_code,
        )
        self.iterator = content

        if ping_interval < 0:
            raise ValueError("argument ping_interval must be not negative")
        self.ping_interval = ping_interval

    def to_asgi_response(
        self,
        app: Litestar | None,
        request: Request,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: Iterable[Cookie] | None = None,
        encoded_headers: Iterable[tuple[bytes, bytes]] | None = None,
        headers: dict[str, str] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
        type_encoders: TypeEncodersMap | None = None,
    ) -> ASGIResponse:
        """Create an ASGIStreamingResponse from a StremaingResponse instance.

        Args:
            app: The :class:`Litestar <.app.Litestar>` application instance.
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
            An ASGIStreamingResponse instance.
        """
        if app is not None:
            warn_deprecation(
                version="2.1",
                deprecated_name="app",
                kind="parameter",
                removal_in="3.0.0",
                alternative="request.app",
            )

        headers = {**headers, **self.headers} if headers is not None else self.headers
        cookies = self.cookies if cookies is None else itertools.chain(self.cookies, cookies)

        media_type = get_enum_string_value(media_type or self.media_type or MediaType.JSON)

        iterator = self.iterator
        if not isinstance(iterator, (Iterable, Iterator, AsyncIterable, AsyncIterator)) and callable(iterator):
            iterator = iterator()

        return ASGIStreamingSSEResponse(
            background=self.background or background,
            content_length=0,
            cookies=cookies,
            encoded_headers=encoded_headers,
            encoding=self.encoding,
            headers=headers,
            is_head_response=is_head_response,
            iterator=iterator,
            media_type=media_type,
            status_code=self.status_code or status_code,
            ping_interval=self.ping_interval,
        )


class ServerSentEvent(SSEStream):
    """docs."""

    def __init__(
        self,
        content: str | bytes | StreamType[SSEData],
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        headers: ResponseHeaders | None = None,
        event_type: str | None = None,
        event_id: int | str | None = None,
        retry_duration: int | None = None,
        comment_message: str | None = None,
        status_code: int | None = None,
        ping_interval: float = 0,
    ) -> None:
        """Initialize the response.

        Args:
            content: Bytes, string or a sync or async iterator or iterable.
            background: A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
                :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished.
                Defaults to None.
            cookies: A list of :class:`Cookie <.datastructures.Cookie>` instances to be set under the response
                ``Set-Cookie`` header.
            encoding: The encoding to be used for the response headers.
            headers: A string keyed dictionary of response headers. Header keys are insensitive.
            status_code: The response status code. Defaults to 200.
            event_type: The type of the SSE event. If given, the browser will sent the event to any 'event-listener'
                declared for it (e.g. via 'addEventListener' in JS).
            event_id: The event ID. This sets the event source's 'last event id'.
            retry_duration: Retry duration in milliseconds.
            comment_message: A comment message. This value is ignored by clients and is used mostly for pinging.
            ping_interval: The interval in seconds between "ping" messages.
        """
        super().__init__(
            content=_ServerSentEventIterator(
                content=content,
                event_type=event_type,
                event_id=event_id,
                retry_duration=retry_duration,
                comment_message=comment_message,
            ),
            media_type="text/event-stream",
            background=background,
            cookies=cookies,
            encoding=encoding,
            headers=headers,
            status_code=status_code,
            ping_interval=ping_interval,
        )
        self.headers.setdefault("Cache-Control", "no-cache")
        self.headers["Connection"] = "keep-alive"
        self.headers["X-Accel-Buffering"] = "no"
