from typing import Any, AsyncGenerator, Generator

import pytest

from litestar.di import Provide


def sync_callable() -> float:
    return 0.1


async def async_callable() -> float:
    return 0.1


def sync_generator() -> Generator[float, None, None]:
    yield 0.1


async def async_generator() -> AsyncGenerator[float, None]:
    yield 0.1


@pytest.mark.parametrize(
    ("dep", "exp"),
    [
        (sync_callable, True),
        (async_callable, False),
        (sync_generator, True),
        pytest.param(async_generator, False, marks=pytest.mark.xfail(reason="the bug")),
    ],
)
def test_dependency_has_async_callable(dep: Any, exp: bool) -> None:
    assert Provide(dep).has_sync_callable is exp
