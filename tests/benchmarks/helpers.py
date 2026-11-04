"""Helpers for driving a Litestar app directly through the ASGI interface.

The benchmarks deliberately avoid ``TestClient``: it runs the app behind an anyio
blocking portal in a separate thread, which adds overhead and is serialised under
Valgrind. Calling ``app(scope, receive, send)`` on a reused event loop measures only
Litestar's own request path; ``ASGIRunner.request_many`` batches several requests into
one event-loop entry so a benchmark measures the request path rather than the loop entry.

``ASGIRunner.lifespan`` starts the app the way a server does, outside the measured call.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, cast

from litestar.types import ASGIApp, HTTPReceiveMessage, HTTPScope, Message, Scope

if TYPE_CHECKING:
    from litestar import Litestar

_DISCONNECT: HTTPReceiveMessage = {"type": "http.disconnect"}


def make_scope(
    path: str = "/",
    *,
    method: str = "GET",
    query_string: bytes = b"",
    headers: Iterable[tuple[bytes, bytes]] = (),
) -> HTTPScope:
    return cast(
        "HTTPScope",
        {
            "type": "http",
            "asgi": {"spec_version": "2.3", "version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "root_path": "",
            "query_string": query_string,
            "headers": [(b"host", b"testserver"), *headers],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "extensions": {},
            "state": {},
        },
    )


def response_status(messages: list[Message]) -> int:
    start = cast("dict[str, Any]", messages[0])
    assert start["type"] == "http.response.start", start
    return cast("int", start["status"])


def response_body(messages: list[Message]) -> bytes:
    return b"".join(cast("dict[str, Any]", message).get("body", b"") for message in messages[1:])


class ASGIRunner:
    def __init__(self) -> None:
        self._runner = asyncio.Runner(loop_factory=asyncio.new_event_loop)
        self._loop = self._runner.get_loop()

    def close(self) -> None:
        self._runner.close()

    @contextmanager
    def lifespan(self, app: Litestar) -> Iterator[None]:
        started = asyncio.Event()
        stop = asyncio.Event()

        async def run() -> None:
            async with app.lifespan():
                started.set()
                await stop.wait()

        task = self._loop.create_task(run())
        self._loop.run_until_complete(started.wait())
        try:
            yield
        finally:
            stop.set()
            self._loop.run_until_complete(task)

    def request_many(self, app: ASGIApp, scope: HTTPScope, body: bytes | None = None, count: int = 10) -> list[Message]:
        messages: list[Message] = []
        request: HTTPReceiveMessage = {"type": "http.request", "body": body or b"", "more_body": False}
        complete = asyncio.Event()
        body_pending = True

        async def send(message: Message) -> None:
            messages.append(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                complete.set()

        async def receive() -> HTTPReceiveMessage:
            nonlocal body_pending
            if body_pending:
                body_pending = False
                return request
            await complete.wait()
            return _DISCONNECT

        async def call() -> None:
            nonlocal body_pending
            for _ in range(count):
                messages.clear()
                body_pending = True
                complete.clear()
                await app(cast("Scope", {**scope, "state": {}}), receive, send)

        self._loop.run_until_complete(call())
        return messages
