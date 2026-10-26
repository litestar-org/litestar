"""Helpers for driving a Litestar app directly through the ASGI interface.

The benchmarks deliberately avoid ``TestClient``: it runs the app behind an anyio
blocking portal in a separate thread, which adds overhead and is serialised under
Valgrind. Calling ``app(scope, receive, send)`` on a reused event loop measures only
Litestar's own request path.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any, cast

from litestar.types import ASGIApp, HTTPScope, Message, Receive, Scope

__all__ = ("ASGIRunner", "make_receive", "make_scope", "response_body", "response_status")


def make_scope(
    path: str = "/",
    *,
    method: str = "GET",
    query_string: bytes = b"",
    headers: Iterable[tuple[bytes, bytes]] = (),
) -> HTTPScope:
    """Build a minimal HTTP ASGI scope. Litestar fills in ``app``, ``path_params`` etc."""
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


async def _unreadable_receive() -> Any:
    raise AssertionError("The benchmark app must not read a request body")


def make_receive(body: bytes) -> Receive:
    """Return a ``receive`` callable that yields ``body`` once, then a disconnect."""
    messages = iter(
        (
            {"type": "http.request", "body": body, "more_body": False},
            {"type": "http.disconnect"},
        )
    )

    async def receive() -> Any:
        return next(messages)

    return receive


def response_status(messages: list[Message]) -> int:
    start = cast("dict[str, Any]", messages[0])
    assert start["type"] == "http.response.start", start
    return cast("int", start["status"])


def response_body(messages: list[Message]) -> bytes:
    return b"".join(cast("dict[str, Any]", message).get("body", b"") for message in messages[1:])


class ASGIRunner:
    """Run ASGI requests on one long-lived event loop."""

    def __init__(self) -> None:
        self._runner = asyncio.Runner()

    def close(self) -> None:
        self._runner.close()

    def request(self, app: ASGIApp, scope: HTTPScope, body: bytes | None = None) -> list[Message]:
        """Send one request to ``app`` and return the messages it sent.

        The scope is shallow-copied and given a fresh ``state`` dict so the same template
        can be reused across benchmark rounds.
        """
        messages: list[Message] = []

        async def send(message: Message) -> None:
            messages.append(message)

        request_scope = cast("Scope", {**scope, "state": {}})
        receive = make_receive(body) if body is not None else _unreadable_receive

        async def call() -> None:
            await app(request_scope, receive, send)

        self._runner.run(call())
        return messages
