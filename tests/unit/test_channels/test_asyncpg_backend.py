from __future__ import annotations

import asyncio
from typing import Any

from litestar.channels.backends.asyncpg import AsyncPgChannelsBackend


class _ConcurrentConnection:
    def __init__(self) -> None:
        self.active_operations = 0
        self.max_active_operations = 0
        self.added_channels: list[str] = []
        self.removed_channels: list[str] = []
        self.closed = False

    async def add_listener(self, channel: str, *args: Any, **kwargs: Any) -> None:
        await self._operation()
        self.added_channels.append(channel)

    async def remove_listener(self, channel: str, *args: Any, **kwargs: Any) -> None:
        await self._operation()
        self.removed_channels.append(channel)

    async def close(self) -> None:
        self.closed = True

    async def _operation(self) -> None:
        self.active_operations += 1
        self.max_active_operations = max(self.max_active_operations, self.active_operations)
        await asyncio.sleep(0)
        self.active_operations -= 1


async def test_listener_mutations_are_serialized() -> None:
    backend = AsyncPgChannelsBackend(make_connection=asyncio.Future)
    connection = _ConcurrentConnection()
    backend._listener_conn = connection  # type: ignore[assignment]

    await asyncio.gather(backend.subscribe(["one"]), backend.subscribe(["two"]))

    assert connection.max_active_operations == 1


async def test_duplicate_listener_mutations_are_idempotent() -> None:
    backend = AsyncPgChannelsBackend(make_connection=asyncio.Future)
    connection = _ConcurrentConnection()
    backend._listener_conn = connection  # type: ignore[assignment]

    await backend.subscribe(channel for channel in ["one", "one"])
    await backend.subscribe(["one"])
    await backend.unsubscribe(channel for channel in ["one", "one"])
    await backend.unsubscribe(["one"])

    assert connection.added_channels == ["one"]
    assert connection.removed_channels == ["one"]


async def test_backend_is_reusable_across_lifecycles() -> None:
    connections = [_ConcurrentConnection(), _ConcurrentConnection()]

    async def make_connection() -> Any:
        return connections.pop(0)

    backend = AsyncPgChannelsBackend(make_connection=make_connection)

    await backend.on_startup()
    first_connection = backend._listener_conn
    await backend.subscribe(["one"])
    await backend.on_shutdown()
    await backend.on_startup()
    second_connection = backend._listener_conn
    await backend.subscribe(["one"])

    assert first_connection.added_channels == ["one"]  # type: ignore[attr-defined]
    assert second_connection.added_channels == ["one"]  # type: ignore[attr-defined]
