from functools import partial
from typing import Callable

import pytest

from starlite.utils import is_async_callable


class AsyncTestCallable:
    async def __call__(self, param1: int, param2: int) -> None:
        ...

    async def method(self, param1: int, param2: int) -> None:
        ...


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
    ],
)
def test_is_async_callable(c: Callable[[int, int], None], exp: bool) -> None:
    assert is_async_callable(c) is exp
    partial_1 = partial(c, 1)
    assert is_async_callable(partial_1) is exp
    partial_2 = partial(partial_1, 2)
    assert is_async_callable(partial_2) is exp
