from __future__ import annotations

import itertools
import re
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator, Callable, Iterable, Iterator
from dataclasses import dataclass
from functools import partial
from io import StringIO
from typing import TYPE_CHECKING, Any

import anyio

from litestar.concurrency import sync_to_thread
from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.streaming import ASGIStreamingResponse, Stream
from litestar.utils import AsyncIteratorWrapper
from litestar.utils.helpers import get_enum_string_value

if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.datastructures.cookie import Cookie
    from litestar.types import Receive, ResponseCookies, ResponseHeaders, Send, SSEData, StreamType, TypeEncodersMap

_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")
DEFAULT_SEPARATOR = "\r\n"


class _ServerSentEventIterator(AsyncIteratorWrapper[bytes]):
    __slots__ = ("comment_message", "content_async_iterator", "event_id", "event_type", "retry_duration")

    content_async_iterator: AsyncIterable[SSEData]

    def __init__(
        self,
        content: str | bytes | StreamType[SSEData] | Callable[[], str | bytes | StreamType[SSEData]],
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
            chunks.extend(f": {chunk}{DEFAULT_SEPARATOR}".encode() for chunk in _LINE_BREAK_RE.split(comment_message))

        if event_id is not None:
            chunks.append(f"id: {event_id}{DEFAULT_SEPARATOR}".encode())

        if event_type is not None:
            chunks.append(f"event: {event_type}{DEFAULT_SEPARATOR}".encode())

        if retry_duration is not None:
            chunks.append(f"retry: {retry_duration}{DEFAULT_SEPARATOR}".encode())

        super().__init__(iterator=chunks)

        if not isinstance(content, (Iterator, AsyncIterator, AsyncIteratorWrapper)) and callable(content):
            content = content()

        if isinstance(content, (str, bytes)):
            self.content_async_iterator = AsyncIteratorWrapper([content])
        elif isinstance(content, Iterable):
            self.content_async_iterator = AsyncIteratorWrapper(content)
        elif isinstance(content, (AsyncIterable, AsyncIteratorWrapper)):
            self.content_async_iterator = content
        else:
            raise ImproperlyConfiguredException(f"Invalid type {type(content)} for ServerSentEvent")

    def ensure_bytes(self, data: str | int | bytes | dict | ServerSentEventMessage, sep: str) -> bytes:
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
        buffer = StringIO()
        if self.comment is not None:
            for chunk in _LINE_BREAK_RE.split(self.comment):
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
    """ASGI streaming response with optional keepalive ping support for SSE."""

    __slots__ = ("_ping_interval", "_send_lock")

    def __init__(self, *, ping_interval: float | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ping_interval = ping_interval
        self._send_lock = anyio.Lock() if ping_interval is not None else None

    async def _send(self, send: Send, payload: bytes) -> None:
        """Send a body chunk, using a lock when ping is enabled for concurrent safety."""
        if self._send_lock is not None:
            async with self._send_lock:
                await send({"type": "http.response.body", "body": payload, "more_body": True})
        else:
            await send({"type": "http.response.body", "body": payload, "more_body": True})

    async def _ping(self, send: Send, stop_event: anyio.Event) -> None:
        """Send SSE comment keepalive pings at the configured interval."""
        assert self._ping_interval is not None  # noqa: S101
        while not stop_event.is_set():
            with anyio.move_on_after(self._ping_interval):
                await stop_event.wait()
            if not stop_event.is_set():
                await self._send(send, b": ping\r\n\r\n")

    async def send_body(self, send: Send, receive: Receive) -> None:
        """Emit the response body, with optional keepalive pings."""
        if self._ping_interval is None:
            await super().send_body(send, receive)
            return

        stop_event = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(partial(self._listen_for_disconnect, tg.cancel_scope, receive))
            tg.start_soon(self._ping, send, stop_event)

            async for chunk in self.iterator:
                payload = chunk if isinstance(chunk, bytes) else chunk.encode(self.encoding)
                await self._send(send, payload)

            stop_event.set()
            tg.cancel_scope.cancel()

        await send({"type": "http.response.body", "body": b"", "more_body": False})


class ServerSentEvent(Stream):
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
        ping_interval: float | None = None,
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
            ping_interval: Interval in seconds between keepalive pings. When set, an SSE comment
                (``: ping``) is sent at the specified interval to prevent connection timeouts from
                reverse proxies or clients. Defaults to ``None`` (no pings).
        """
        self.ping_interval = ping_interval
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
        )
        self.headers.setdefault("Cache-Control", "no-cache")
        self.headers["Connection"] = "keep-alive"
        self.headers["X-Accel-Buffering"] = "no"

    def to_asgi_response(
        self,
        request: Request,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: Iterable[Cookie] | None = None,
        headers: dict[str, str] | None = None,
        is_head_response: bool = False,
        media_type: MediaType | str | None = None,
        status_code: int | None = None,
        type_encoders: TypeEncodersMap | None = None,
    ) -> ASGIStreamingSSEResponse:
        """Create an ASGIStreamingSSEResponse with optional keepalive ping support.

        Args:
            background: Background task(s) to be executed after the response is sent.
            cookies: A list of cookies to be set on the response.
            headers: Additional headers to be merged with the response headers. Response headers take precedence.
            is_head_response: Whether the response is a HEAD response.
            media_type: Media type for the response. If ``media_type`` is already set on the response, this is ignored.
            request: The :class:`Request <.connection.Request>` instance.
            status_code: Status code for the response. If ``status_code`` is already set on the response, this is
                ignored.
            type_encoders: A dictionary of type encoders to use for encoding the response content.

        Returns:
            An ASGIStreamingSSEResponse instance.
        """
        headers = {**headers, **self.headers} if headers is not None else self.headers
        cookies = self.cookies if cookies is None else itertools.chain(self.cookies, cookies)
        media_type = get_enum_string_value(media_type or self.media_type or MediaType.JSON)

        iterator = self.iterator
        if not isinstance(iterator, (Iterable, Iterator, AsyncIterable, AsyncIterator)) and callable(iterator):
            iterator = iterator()

        return ASGIStreamingSSEResponse(
            ping_interval=self.ping_interval,
            background=self.background or background,
            content_length=0,
            cookies=cookies,
            encoding=self.encoding,
            headers=headers,
            is_head_response=is_head_response,
            iterator=iterator,
            media_type=media_type,
            status_code=self.status_code or status_code,
        )
