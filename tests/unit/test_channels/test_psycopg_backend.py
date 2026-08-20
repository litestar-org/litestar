from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from litestar.channels.backends.psycopg import PsycoPgChannelsBackend


class _ConcurrentConnection:
    def __init__(self) -> None:
        self.active_operations = 0
        self.max_active_operations = 0

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        self.active_operations += 1
        self.max_active_operations = max(self.max_active_operations, self.active_operations)
        await asyncio.sleep(0)
        self.active_operations -= 1

    async def commit(self) -> None:
        return None


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


async def test_subscription_mutations_are_serialized() -> None:
    backend = PsycoPgChannelsBackend("postgresql://unused")
    connection = _ConcurrentConnection()
    backend._listener_conn = connection  # type: ignore[assignment]

    await asyncio.gather(backend.subscribe(["one"]), backend.subscribe(["two"]))

    assert connection.max_active_operations == 1


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
