from functools import partial
from typing import Awaitable, Callable

import pytest
from anyio.to_thread import run_sync

from starlite.utils.lifecycle_hooks import LifecycleHook


@pytest.fixture
def sync_callable() -> Callable[[str], str]:
    def f(s: str) -> str:
        return f"sync callable: {s}"

    return f


@pytest.fixture
def sync_hook(sync_callable: Callable[[str], str]) -> LifecycleHook:
    return LifecycleHook(sync_callable)


@pytest.fixture
def async_callable() -> Callable[[str], Awaitable[str]]:
    async def f(s: str) -> str:
        return f"async callable: {s}"

    return f


@pytest.fixture
def async_hook(async_callable: Callable[[str], Awaitable[str]]) -> LifecycleHook:
    return LifecycleHook(async_callable)


def test_init_lifecycle_hook_sync_callable(sync_callable: Callable[[str], str], sync_hook: LifecycleHook) -> None:
    assert isinstance(sync_hook.wrapped[0], partial)
    assert sync_hook.wrapped[0].func is run_sync
    assert sync_hook.wrapped[0].args == (sync_callable,)


def test_init_lifecycle_hook_async_callable(
    async_callable: Callable[[str], Awaitable[str]], async_hook: LifecycleHook
) -> None:
    assert async_hook.wrapped[0] is async_callable


async def test_call_sync_hook(sync_hook: LifecycleHook) -> None:
    assert await sync_hook("called") == "sync callable: called"


async def test_call_async_hook(async_hook: LifecycleHook) -> None:
    assert await async_hook("called") == "async callable: called"
