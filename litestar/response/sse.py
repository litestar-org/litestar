from __future__ import annotations

import re
from typing import TYPE_CHECKING, AsyncGenerator, AsyncIterable, AsyncIterator, Iterable, Iterator

from anyio.to_thread import run_sync

from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.streaming import Stream
from litestar.utils import AsyncIteratorWrapper

if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.types import ResponseCookies, ResponseHeaders, StreamType

_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")


class _ServerSentEventIterator(AsyncIteratorWrapper[bytes]):
    __slots__ = ("content_async_iterator",)

    content_async_iterator: AsyncIteratorWrapper[bytes | str] | AsyncIterable[str | bytes] | AsyncIterator[str | bytes]

    def __init__(
        self,
        content: str | bytes | StreamType[str | bytes],
        event_type: str | None = None,
        event_id: int | None = None,
        retry_duration: int | None = None,
        comment_message: str | None = None,
    ) -> None:
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
            self.content_async_iterator = AsyncIteratorWrapper(content)  # type: ignore[arg-type]
        elif isinstance(content, (AsyncIterable, AsyncIterator, AsyncIteratorWrapper)):
            self.content_async_iterator = content
        else:
            raise ImproperlyConfiguredException(f"Invalid type {type(content)} for ServerSentEvent")

    def _call_next(self) -> bytes:
        try:
            return next(self.iterator)
        except StopIteration as e:
            raise ValueError from e

    async def _async_generator(self) -> AsyncGenerator[bytes, None]:
        while True:
            try:
                yield await run_sync(self._call_next)
            except ValueError:
                async for value in self.content_async_iterator:
                    yield f"data: {value}\r\n".encode() if isinstance(value, str) else b"data: {" + value + b"}\r\n"
                break
        yield b"\r\n"


class ServerSentEvent(Stream):
    def __init__(
        self,
        content: str | bytes | StreamType[str | bytes],
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: ResponseCookies | None = None,
        encoding: str = "utf-8",
        headers: ResponseHeaders | None = None,
        event_type: str | None = None,
        event_id: int | None = None,
        retry_duration: int | None = None,
        comment_message: str | None = None,
        status_code: int | None = None,
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
        )
        self.headers.setdefault("Cache-Control", "no-cache")
        self.headers["Connection"] = "keep-alive"
        self.headers["X-Accel-Buffering"] = "no"
