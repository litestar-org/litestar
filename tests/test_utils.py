from functools import partial
from typing import AsyncGenerator, Callable

import pytest

from litestar.utils import is_async_callable


class AsyncTestCallable:
    async def __call__(self, param1: int, param2: int) -> None:
        ...

    async def method(self, param1: int, param2: int) -> None:
        ...


async def async_generator() -> AsyncGenerator[int, None]:
    yield 1


class SyncTestCallable:
    def __call__(self, param1: int, param2: int) -> None:
        ...

    def method(self, param1: int, param2: int) -> None:
        ...


async def async_func(param1: int, param2: int) -> None:
    ...


def sync_func(param1: int, param2: int) -> None:
    ...


async_callable = AsyncTestCallable()
sync_callable = SyncTestCallable()


@pytest.mark.parametrize(
    "c, exp",
    [
        (async_callable, True),
        (sync_callable, False),
        (async_callable.method, True),
        (sync_callable.method, False),
        (async_func, True),
        (sync_func, False),
        (lambda: ..., False),
        (AsyncTestCallable, True),
        (SyncTestCallable, False),
        (async_generator, False),
    ],
)
def test_is_async_callable(c: Callable[[int, int], None], exp: bool) -> None:
    assert is_async_callable(c) is exp
    partial_1 = partial(c, 1)
    assert is_async_callable(partial_1) is exp
    partial_2 = partial(partial_1, 2)
    assert is_async_callable(partial_2) is exp
