from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import trio
from pytest_mock import MockerFixture

from litestar.concurrency import (
    get_asyncio_executor,
    get_trio_capacity_limiter,
    set_asyncio_executor,
    set_trio_capacity_limiter,
    sync_to_thread,
)


def func() -> int:
    return 1


def test_sync_to_thread_asyncio() -> None:
    loop = asyncio.new_event_loop()
    assert loop.run_until_complete(sync_to_thread(func)) == 1


def test_sync_to_thread_trio() -> None:
    assert trio.run(sync_to_thread, func) == 1


def test_get_set_asyncio_executor() -> None:
    assert get_asyncio_executor() is None
    executor = ThreadPoolExecutor()
    set_asyncio_executor(executor)
    assert get_asyncio_executor() is executor


def test_get_set_trio_capacity_limiter() -> None:
    limiter = trio.CapacityLimiter(10)
    assert get_trio_capacity_limiter() is None
    set_trio_capacity_limiter(limiter)
    assert get_trio_capacity_limiter() is limiter


def test_asyncio_uses_executor(mocker: MockerFixture) -> None:
    executor = ThreadPoolExecutor()

    mocker.patch("litestar.concurrency.get_asyncio_executor", return_value=executor)
    mock_run_in_executor = AsyncMock()
    mocker.patch("litestar.concurrency.asyncio.get_running_loop").return_value.run_in_executor = mock_run_in_executor

    loop = asyncio.new_event_loop()
    loop.run_until_complete(sync_to_thread(func))

    assert mock_run_in_executor.call_args_list[0].args[0] is executor


def test_trio_uses_limiter(mocker: MockerFixture) -> None:
    limiter = trio.CapacityLimiter(10)
    mocker.patch("litestar.concurrency.get_trio_capacity_limiter", return_value=limiter)
    mock_run_sync = mocker.patch("trio.to_thread.run_sync", new_callable=AsyncMock)

    trio.run(sync_to_thread, func)

    assert mock_run_sync.call_args_list[0].kwargs["limiter"] is limiter
