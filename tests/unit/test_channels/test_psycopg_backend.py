from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator

import pytest
from psycopg import AsyncConnection

from litestar.channels.backends.psycopg import PsycoPgChannelsBackend


class _ConcurrentConnection:
    def __init__(self) -> None:
        self.active_operations = 0
        self.max_active_operations = 0

    async def __aenter__(self) -> _ConcurrentConnection:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        self.active_operations += 1
        self.max_active_operations = max(self.max_active_operations, self.active_operations)
        await asyncio.sleep(0)
        self.active_operations -= 1

    async def commit(self) -> None:
        return None

    def notifies(self, *, timeout: float | None = None, stop_after: int | None = None) -> Any:
        return self._no_notifications()

    @staticmethod
    async def _no_notifications() -> AsyncGenerator[Any, None]:
        await asyncio.sleep(0.01)
        nothing: Any
        for nothing in ():
            yield nothing


class _FailingConnection(_ConcurrentConnection):
    def notifies(self, *, timeout: float | None = None, stop_after: int | None = None) -> _FailingNotifications:
        return _FailingNotifications()


class _FailingNotifications:
    def __aiter__(self) -> _FailingNotifications:
        return self

    async def __anext__(self) -> Any:
        raise RuntimeError("listener failed")


@dataclass
class _Notification:
    channel: str
    payload: str


@pytest.fixture()
def stub_connection() -> _ConcurrentConnection:
    return _ConcurrentConnection()


@pytest.fixture()
async def started_backend(
    monkeypatch: pytest.MonkeyPatch, stub_connection: _ConcurrentConnection
) -> AsyncGenerator[PsycoPgChannelsBackend, None]:
    async def fake_connect(*args: Any, **kwargs: Any) -> _ConcurrentConnection:
        return stub_connection

    monkeypatch.setattr(AsyncConnection, "connect", fake_connect)

    backend = PsycoPgChannelsBackend("postgresql://unused")
    await backend.on_startup()
    yield backend
    await backend.on_shutdown()


async def test_subscription_mutations_are_serialized(
    started_backend: PsycoPgChannelsBackend, stub_connection: _ConcurrentConnection
) -> None:
    await asyncio.gather(started_backend.subscribe(["one"]), started_backend.subscribe(["two"]))

    assert stub_connection.max_active_operations == 1


async def test_stream_events_propagates_listener_failures() -> None:
    backend = PsycoPgChannelsBackend("postgresql://unused")
    backend._listener_conn = _FailingConnection()  # type: ignore[assignment]
    backend._start_listener()

    with pytest.raises(RuntimeError, match="listener failed"):
        await backend.stream_events().__anext__()


async def test_stream_events_filters_queued_events_after_unsubscribe() -> None:
    backend = PsycoPgChannelsBackend("postgresql://unused")
    backend._subscribed_channels.add("retained")
    backend._event_queue.put_nowait(("removed", b"old"))
    backend._event_queue.put_nowait(("retained", b"new"))

    assert await backend.stream_events().__anext__() == ("retained", b"new")
