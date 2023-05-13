from functools import partial
from typing import Any, AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest

from litestar._kwargs.cleanup import DependencyCleanupGroup
from litestar.di import Provide
from litestar.exceptions import LitestarWarning
from litestar.types import Empty
from litestar.utils.compat import async_next


class C:
    val = 31

    def __init__(self) -> None:
        self.val = 13

    @classmethod
    async def async_class(cls) -> int:
        return cls.val

    @classmethod
    def sync_class(cls) -> int:
        return cls.val

    @staticmethod
    async def async_static() -> str:
        return "one-three"

    @staticmethod
    def sync_static() -> str:
        return "one-three"

    async def async_instance(self) -> int:
        return self.val

    def sync_instance(self) -> int:
        return self.val


async def async_fn(val: str = "three-one") -> str:
    return val


def sync_fn(val: str = "three-one") -> str:
    return val


async_partial = partial(async_fn, "why-three-and-one")
sync_partial = partial(sync_fn, "why-three-and-one")


async def test_provide_default(anyio_backend: str) -> None:
    provider = Provide(dependency=async_fn)
    value = await provider()
    assert value == "three-one"


async def test_provide_cached(anyio_backend: str) -> None:
    provider = Provide(dependency=async_fn, use_cache=True)
    assert provider.value is Empty
    value = await provider()
    assert value == "three-one"
    assert provider.value == value
    second_value = await provider()
    assert value == second_value
    third_value = await provider()
    assert value == third_value


async def test_run_in_thread(anyio_backend: str) -> None:
    provider = Provide(dependency=sync_fn, sync_to_thread=True)
    value = await provider()
    assert value == "three-one"


def test_provider_equality_check() -> None:
    first_provider = Provide(dependency=sync_fn, sync_to_thread=False)
    second_provider = Provide(dependency=sync_fn, sync_to_thread=False)
    assert first_provider == second_provider
    third_provider = Provide(dependency=sync_fn, use_cache=True, sync_to_thread=False)
    assert first_provider != third_provider
    second_provider.value = True
    assert first_provider != second_provider


@pytest.mark.parametrize(
    "fn, exp",
    [
        (C.async_class, 31),
        (C.sync_class, 31),
        (C.async_static, "one-three"),
        (C.sync_static, "one-three"),
        (C().async_instance, 13),
        (C().sync_instance, 13),
        (async_fn, "three-one"),
        (sync_fn, "three-one"),
        (async_partial, "why-three-and-one"),
        (sync_partial, "why-three-and-one"),
    ],
)
@pytest.mark.usefixtures("disable_warn_sync_to_thread_with_async")
async def test_provide_for_callable(fn: Any, exp: Any, anyio_backend: str) -> None:
    assert await Provide(fn, sync_to_thread=False)() == exp


@pytest.fixture
def cleanup_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def async_cleanup_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def generator(cleanup_mock: MagicMock) -> Generator[str, None, None]:
    def func() -> Generator[str, None, None]:
        yield "hello"
        cleanup_mock()

    return func()


@pytest.fixture
def async_generator(async_cleanup_mock: MagicMock) -> AsyncGenerator[str, None]:
    async def func() -> AsyncGenerator[str, None]:
        yield "world"
        async_cleanup_mock()

    return func()


def test_cleanup_group_add(generator: Generator[str, None, None]) -> None:
    group = DependencyCleanupGroup()

    group.add(generator)

    assert group._generators == [generator]


async def test_cleanup_group_cleanup(generator: Generator[str, None, None], cleanup_mock: MagicMock) -> None:
    next(generator)
    group = DependencyCleanupGroup([generator])

    await group.cleanup()

    cleanup_mock.assert_called_once()
    assert group._closed


async def test_cleanup_group_cleanup_multiple(
    generator: Generator[str, None, None],
    async_generator: AsyncGenerator[str, None],
    cleanup_mock: MagicMock,
    async_cleanup_mock: MagicMock,
) -> None:
    next(generator)
    await async_next(async_generator)
    group = DependencyCleanupGroup([generator, async_generator])

    await group.cleanup()

    cleanup_mock.assert_called_once()
    async_cleanup_mock.assert_called_once()
    assert group._closed


async def test_cleanup_group_cleanup_on_closed_raises(generator: Generator[str, None, None]) -> None:
    next(generator)
    group = DependencyCleanupGroup([generator])

    await group.cleanup()
    with pytest.raises(RuntimeError):
        await group.cleanup()


async def test_cleanup_group_add_on_closed_raises(
    generator: Generator[str, None, None], async_generator: AsyncGenerator[str, None]
) -> None:
    next(generator)
    group = DependencyCleanupGroup([generator])

    await group.cleanup()

    with pytest.raises(RuntimeError):
        group.add(async_generator)


@pytest.mark.usefixtures("enable_warn_implicit_sync_to_thread")
def test_sync_callable_without_sync_to_thread_warns() -> None:
    def func() -> None:
        pass

    with pytest.warns(LitestarWarning, match="discouraged since synchronous callables"):
        Provide(func)


@pytest.mark.parametrize("sync_to_thread", [True, False])
def test_async_callable_with_sync_to_thread_warns(sync_to_thread: bool) -> None:
    async def func() -> None:
        pass

    with pytest.warns(LitestarWarning, match="asynchronous callable"):
        Provide(func, sync_to_thread=sync_to_thread)
