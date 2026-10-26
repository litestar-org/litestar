from __future__ import annotations

import asyncio
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar.types import ASGIApp, HTTPReceiveMessage, Message


class ASGIDriver:
    """Drive an ASGI application in-process, without a test client or server.

    This keeps the benchmarks focused on the framework's request handling path, avoiding the overhead
    (threads, portals, HTTP clients) a regular test client would add to the measurements.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def request(
        self,
        app: ASGIApp,
        method: str = "GET",
        path: str = "/",
        query_string: bytes = b"",
        headers: list[tuple[bytes, bytes]] | None = None,
        body: bytes = b"",
    ) -> tuple[int, bytes]:
        return self.loop.run_until_complete(self._request(app, method, path, query_string, headers or [], body))

    @staticmethod
    async def _request(
        app: ASGIApp,
        method: str,
        path: str,
        query_string: bytes,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> tuple[int, bytes]:
        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "root_path": "",
            "query_string": query_string,
            "headers": [(b"host", b"testserver"), *headers],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "state": {},
        }
        body_sent = False
        status = 0
        chunks: list[bytes] = []

        async def receive() -> HTTPReceiveMessage:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await app(scope, receive, send)  # type: ignore[arg-type]
        return status, b"".join(chunks)


@pytest.fixture()
def asgi_driver() -> Generator[ASGIDriver, None, None]:
    loop = asyncio.new_event_loop()
    try:
        yield ASGIDriver(loop)
    finally:
        loop.close()


@pytest.fixture()
def run_async() -> Generator[Callable[[Any], Any], None, None]:
    loop = asyncio.new_event_loop()
    try:
        yield loop.run_until_complete
    finally:
        loop.close()
