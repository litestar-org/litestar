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
from collections.abc import Coroutine, Iterable, Iterator
from contextlib import contextmanager, suppress
from typing import Any, cast

from litestar.types import (
    ASGIApp,
    HTTPReceiveMessage,
    HTTPScope,
    LifeSpanReceiveMessage,
    LifeSpanSendMessage,
    Message,
    Receive,
    Scope,
    Send,
)

_RESPONSE_TIMEOUT = 10.0


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


class _Exchange:
    __slots__ = ("_body", "_body_pending", "_response_complete", "_waiter", "messages")

    def __init__(self, body: bytes | None, messages: list[Message]) -> None:
        self.messages = messages
        self._body = body or b""
        self._body_pending = True
        self._response_complete = False
        self._waiter: asyncio.Event | None = None

    def reset(self) -> None:
        self.messages.clear()
        self._body_pending = True
        self._response_complete = False
        self._waiter = None

    async def send(self, message: Message) -> None:
        self.messages.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            self._response_complete = True
            if self._waiter is not None:
                self._waiter.set()

    async def receive(self) -> HTTPReceiveMessage:
        if self._body_pending:
            self._body_pending = False
            return {"type": "http.request", "body": self._body, "more_body": False}

        if not self._response_complete:
            if self._waiter is None:
                self._waiter = asyncio.Event()
            try:
                async with asyncio.timeout(_RESPONSE_TIMEOUT):
                    await self._waiter.wait()
            except TimeoutError:
                raise AssertionError(
                    "The response did not complete. A benchmark whose response ends only when the "
                    "client disconnects needs a 'receive' that disconnects on its own."
                ) from None

        return {"type": "http.disconnect"}


class ASGIRunner:
    def __init__(self) -> None:
        self._runner = asyncio.Runner(loop_factory=asyncio.new_event_loop)
        self._loop = self._runner.get_loop()

    def close(self) -> None:
        self._runner.close()

    def _run(self, coro: Coroutine[Any, Any, None]) -> None:
        task = self._loop.create_task(coro)
        try:
            self._loop.run_until_complete(task)
        except BaseException:
            task.cancel()
            with suppress(BaseException):
                self._loop.run_until_complete(task)
            raise

    @contextmanager
    def lifespan(self, app: ASGIApp) -> Iterator[None]:
        parked: dict[str, Any] = {}
        scope = cast("Scope", {"type": "lifespan", "asgi": {"spec_version": "2.3", "version": "3.0"}, "state": {}})

        async def startup() -> None:
            queue: asyncio.Queue[LifeSpanReceiveMessage] = asyncio.Queue()
            started = asyncio.Event()
            failures: list[str] = []

            async def receive() -> LifeSpanReceiveMessage:
                return await queue.get()

            async def send(message: LifeSpanSendMessage) -> None:
                if message["type"] == "lifespan.startup.failed":
                    failures.append(message["message"])
                if message["type"] in {"lifespan.startup.complete", "lifespan.startup.failed"}:
                    started.set()

            task = asyncio.ensure_future(app(scope, cast("Receive", receive), cast("Send", send)))
            queue.put_nowait({"type": "lifespan.startup"})
            waiter = asyncio.ensure_future(started.wait())
            try:
                await asyncio.wait({task, waiter}, return_when=asyncio.FIRST_COMPLETED)
            finally:
                waiter.cancel()

            if failures or task.done():
                if not task.done():
                    task.cancel()
                error: BaseException | None = None
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except BaseException as exc:
                    error = exc
                detail = failures[0] if failures else repr(error) if error else "it ended before startup completed"
                raise AssertionError(f"The app's lifespan startup failed: {detail}")

            parked["queue"] = queue
            parked["task"] = task

        async def shutdown() -> None:
            parked["queue"].put_nowait({"type": "lifespan.shutdown"})
            await parked["task"]

        self._run(startup())
        try:
            yield
        finally:
            self._run(shutdown())

    def request_many(self, app: ASGIApp, scope: HTTPScope, body: bytes | None = None, count: int = 10) -> list[Message]:
        messages: list[Message] = []
        exchange = _Exchange(body, messages)
        receive, send = exchange.receive, exchange.send

        async def call() -> None:
            for _ in range(count):
                exchange.reset()
                await app(cast("Scope", {**scope, "state": {}}), receive, send)

        self._run(call())
        return messages
