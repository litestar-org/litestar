from __future__ import annotations

import asyncio
from asyncio import AbstractEventLoop
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from litestar.concurrency import (
    _State,
    get_asyncio_executor,
    set_asyncio_executor,
    sync_to_thread,
)


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    _State.EXECUTOR = None
    yield
    _State.EXECUTOR = None


def func() -> int:
    return 1


@pytest.fixture()
def loop() -> Iterator[AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


def test_sync_to_thread_asyncio(loop: AbstractEventLoop) -> None:
    assert loop.run_until_complete(sync_to_thread(func)) == 1


def test_get_set_asyncio_executor() -> None:
    assert get_asyncio_executor() is None
    executor = ThreadPoolExecutor()
    set_asyncio_executor(executor)
    assert get_asyncio_executor() is executor


def test_asyncio_uses_executor(mocker: MockerFixture, loop: AbstractEventLoop) -> None:
    executor = ThreadPoolExecutor()

    mocker.patch("litestar.concurrency.get_asyncio_executor", return_value=executor)
    mock_run_in_executor = AsyncMock()
    mocker.patch("litestar.concurrency.asyncio.get_running_loop").return_value.run_in_executor = mock_run_in_executor

    loop.run_until_complete(sync_to_thread(func))
    assert mock_run_in_executor.call_args_list[0].args[0] is executor


def test_set_asyncio_executor_from_running_loop_raises(loop: AbstractEventLoop) -> None:
    async def main() -> None:
        set_asyncio_executor(ThreadPoolExecutor())

    with pytest.raises(RuntimeError):
        loop.run_until_complete(main())

    assert get_asyncio_executor() is None
