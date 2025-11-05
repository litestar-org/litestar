from collections.abc import AsyncGenerator, Generator
from functools import partial
from typing import Any

import pytest

from litestar.di import Provide
from litestar.exceptions import ImproperlyConfiguredException, LitestarWarning
from litestar.types import Empty


def generator_func() -> Generator[float, None, None]:
    yield 0.1


async def async_generator_func() -> AsyncGenerator[float, None]:
    yield 0.1


class SyncGeneratorCallable:
    def __init__(self):
        self.call_count = 0
        self.cleanup_count = 0

    def __call__(self) -> Generator[int, None, None]:
        self.call_count += 1

        try:
            yield self.call_count
        finally:
            # Cleanup: remove the session
            self.cleanup_count += 1


class AsyncGeneratorCallable:
    def __init__(self):
        self.call_count = 0
        self.cleanup_count = 0

    async def __call__(self) -> AsyncGenerator[int, None, None]:
        self.call_count += 1

        try:
            yield self.call_count
        finally:
            # Cleanup: remove the session
            self.cleanup_count += 1


async def async_callable(val: str = "three-one") -> str:
    return val


def sync_callable(val: str = "three-one") -> str:
    return val


async_partial = partial(async_callable, "why-three-and-one")
sync_partial = partial(sync_callable, "why-three-and-one")


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


async def test_provide_default(anyio_backend: str) -> None:
    provider = Provide(dependency=async_callable)
    value = await provider()
    assert value == "three-one"


async def test_provide_cached(anyio_backend: str) -> None:
    provider = Provide(dependency=async_callable, use_cache=True)
    assert provider.value is Empty
    value = await provider()
    assert value == "three-one"
    assert provider.value == value
    second_value = await provider()
    assert value == second_value
    third_value = await provider()
    assert value == third_value


async def test_run_in_thread(anyio_backend: str) -> None:
    provider = Provide(dependency=sync_callable, sync_to_thread=True)
    value = await provider()
    assert value == "three-one"


def test_provider_equality_check() -> None:
    first_provider = Provide(dependency=sync_callable, sync_to_thread=False)
    second_provider = Provide(dependency=sync_callable, sync_to_thread=False)
    assert first_provider == second_provider
    third_provider = Provide(dependency=sync_callable, use_cache=True, sync_to_thread=False)
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
        (async_callable, "three-one"),
        (sync_callable, "three-one"),
        (async_partial, "why-three-and-one"),
        (sync_partial, "why-three-and-one"),
    ],
)
@pytest.mark.usefixtures("disable_warn_sync_to_thread_with_async")
async def test_provide_for_callable(fn: Any, exp: Any, anyio_backend: str) -> None:
    assert await Provide(fn, sync_to_thread=False)() == exp


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


def test_generator_with_sync_to_thread_warns() -> None:
    def func() -> Generator[int, None, None]:
        yield 1

    with pytest.warns(LitestarWarning, match="Use of generator"):
        Provide(func, sync_to_thread=True)


@pytest.mark.parametrize(
    ("dep", "exp"),
    [
        (sync_callable, True),
        (async_callable, False),
        (generator_func, True),
        (async_generator_func, True),
        (SyncGeneratorCallable(), True),
    ],
)
def test_dependency_has_async_callable(dep: Any, exp: bool) -> None:
    assert Provide(dep).has_sync_callable is exp


@pytest.mark.parametrize(
    ("dep", "exp"),
    [
        (generator_func, True),
        (async_generator_func, False),
        (SyncGeneratorCallable(), True),
        (AsyncGeneratorCallable(), False),
    ],
)
def test_dependency_has_sync_generator(dep: Any, exp: bool) -> None:
    assert Provide(dep).has_sync_generator_dependency is exp


@pytest.mark.parametrize(
    ("dep", "exp"),
    [
        (generator_func, False),
        (async_generator_func, True),
        (SyncGeneratorCallable(), False),
        (AsyncGeneratorCallable(), True),
    ],
)
def test_dependency_has_async_generator(dep: Any, exp: bool) -> None:
    assert Provide(dep).has_async_generator_dependency is exp


def test_raises_when_dependency_is_not_callable() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Provide(123)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("dep",),
    [
        (generator_func,),
        (async_generator_func,),
    ],
)
def test_raises_when_generator_dependency_is_cached(dep: Any) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        Provide(dep, use_cache=True)


def test_provide_raises_on_unsafe_signature_access() -> None:
    async def foo() -> None:
        pass

    provide = Provide(foo)

    with pytest.raises(ValueError):
        provide.signature_model

    with pytest.raises(ValueError):
        provide.parsed_fn_signature


@pytest.mark.parametrize(
    ("factory_class", "is_async"),
    [
        (SyncGeneratorCallable, False),
        (AsyncGeneratorCallable, True),
    ],
)
@pytest.mark.asyncio
async def test_stateful_generator_with_cleanup(
    factory_class: type[SyncGeneratorCallable] | type[AsyncGeneratorCallable],
    is_async: bool,
) -> None:
    """Verify that stateful callable instances maintain state and execute cleanup."""
    factory = factory_class()
    provide = Provide(factory, sync_to_thread=None)

    # Verify it's detected as the correct generator type
    assert provide.has_sync_generator_dependency is not is_async
    assert provide.has_async_generator_dependency is is_async

    # First call - await the Provide call
    gen1 = await provide()

    # Get first value (sync or async)
    if is_async:
        assert isinstance(gen1, AsyncGenerator)
        session1 = await gen1.__anext__()
    else:
        assert isinstance(gen1, Generator)
        session1 = next(gen1)

    assert session1 == 1
    assert factory.call_count == 1
    assert factory.cleanup_count == 0

    # Second call (state should be maintained)
    gen2 = await provide()

    if is_async:
        session2 = await gen2.__anext__()
    else:
        session2 = next(gen2)

    assert session2 == 2
    assert factory.call_count == 2
    assert factory.cleanup_count == 0

    # Cleanup first generator
    if is_async:
        with pytest.raises(StopAsyncIteration):
            await gen1.__anext__()
    else:
        with pytest.raises(StopIteration):
            next(gen1)

    assert factory.cleanup_count == 1

    # Cleanup second generator
    if is_async:
        with pytest.raises(StopAsyncIteration):
            await gen2.__anext__()
    else:
        with pytest.raises(StopIteration):
            next(gen2)

    assert factory.cleanup_count == 2
