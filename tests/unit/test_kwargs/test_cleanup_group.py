from __future__ import annotations

import sys
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

import pytest

from litestar._kwargs.cleanup import DependencyCleanupGroup
from litestar.utils.compat import async_next


@pytest.fixture
def cleanup_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def async_cleanup_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def generator(cleanup_mock: MagicMock) -> Generator[str, None, None]:
    def func() -> Generator[str, None, None]:
        try:
            yield "hello"
        finally:
            cleanup_mock()

    return func()


@pytest.fixture
def async_generator(async_cleanup_mock: MagicMock) -> AsyncGenerator[str, None]:
    async def func() -> AsyncGenerator[str, None]:
        try:
            yield "world"
        finally:
            async_cleanup_mock()

    return func()


def test_add(generator: Generator[str, None, None]) -> None:
    group = DependencyCleanupGroup()

    group.add(generator)

    assert group._generators == [generator]


async def test_cleanup(generator: Generator[str, None, None], cleanup_mock: MagicMock) -> None:
    next(generator)
    group = DependencyCleanupGroup([generator])

    await group.close()

    cleanup_mock.assert_called_once()
    assert group._closed


async def test_cleanup_throw_multiple_exceptions(
    generator: Generator[str, None, None],
    async_generator: AsyncGenerator[str, None],
    cleanup_mock: MagicMock,
    async_cleanup_mock: MagicMock,
) -> None:
    next(generator)
    await async_next(async_generator)

    group = DependencyCleanupGroup([generator, async_generator])

    await group.close(ValueError())

    cleanup_mock.assert_called_once()
    async_cleanup_mock.assert_called_once()
    assert group._closed


@pytest.mark.parametrize("exit_exception", (None, ValueError()))
async def test_exception_during_close(
    cleanup_mock: MagicMock,
    async_cleanup_mock: MagicMock,
    exit_exception: Exception | None,
) -> None:
    gen_exc = ValueError()

    def gen_fn() -> Generator[None, None, None]:
        try:
            yield
        finally:
            cleanup_mock()
            raise gen_exc  # raise an exception here

    async def async_gen_fn() -> AsyncGenerator[None, None]:
        try:
            yield
        finally:
            async_cleanup_mock()  # we expect this to be called still

    gen_1 = gen_fn()
    gen_2 = async_gen_fn()
    next(gen_1)
    await async_next(gen_2)
    group = DependencyCleanupGroup([gen_1, gen_2])

    with pytest.raises(ExceptionGroup) as exc:
        await group.close(exit_exception)

    assert exc.value.exceptions == (gen_exc,)

    cleanup_mock.assert_called_once()
    async_cleanup_mock.assert_called_once()
    assert group._closed


async def test_cleanup_on_closed_raises(generator: Generator[str, None, None]) -> None:
    next(generator)
    group = DependencyCleanupGroup([generator])

    await group.close()
    with pytest.raises(RuntimeError):
        await group.close()


async def test_add_on_closed_raises(
    generator: Generator[str, None, None], async_generator: AsyncGenerator[str, None]
) -> None:
    next(generator)
    group = DependencyCleanupGroup([generator])

    await group.close()

    with pytest.raises(RuntimeError):
        group.add(async_generator)
