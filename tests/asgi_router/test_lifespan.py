from __future__ import annotations
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator, Callable
from unittest.mock import AsyncMock

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

import pytest

from litestar.testing import create_test_client


class _LifeSpanCallable:
    def __init__(self, should_raise: bool = False) -> None:
        self.called = False
        self.should_raise = should_raise

    def __call__(self) -> None:
        self.called = True
        if self.should_raise:
            raise RuntimeError("damn")


def test_life_span_startup() -> None:
    life_span_callable = _LifeSpanCallable()
    with create_test_client([], on_startup=[life_span_callable]):
        assert life_span_callable.called


def test_life_span_startup_error_handling() -> None:
    life_span_callable = _LifeSpanCallable(should_raise=True)
    with pytest.raises(RuntimeError), create_test_client([], on_startup=[life_span_callable]):
        pass


def test_life_span_shutdown() -> None:
    life_span_callable = _LifeSpanCallable()
    with create_test_client([], on_shutdown=[life_span_callable]):
        pass
    assert life_span_callable.called


def test_life_span_shutdown_error_handling() -> None:
    life_span_callable = _LifeSpanCallable(should_raise=True)
    with pytest.raises(RuntimeError), create_test_client([], on_shutdown=[life_span_callable]):
        pass


@pytest.fixture
def startup_mock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def shutdown_mock() -> AsyncMock:
    return AsyncMock()


LifeSpanManager = Callable[[], "AbstractAsyncContextManager[None]"]


def create_lifespan_manager(startup_mock: AsyncMock, shutdown_mock: AsyncMock) -> LifeSpanManager:
    @asynccontextmanager
    async def lifespan() -> AsyncGenerator[None, None]:
        try:
            await startup_mock()
            yield
        finally:
            await shutdown_mock()

    return lifespan


@pytest.fixture()
def lifespan_manager(startup_mock: AsyncMock, shutdown_mock: AsyncMock) -> LifeSpanManager:
    return create_lifespan_manager(startup_mock, shutdown_mock)


def test_lifespan_context_manager(
    lifespan_manager: LifeSpanManager, startup_mock: AsyncMock, shutdown_mock: AsyncMock
) -> None:
    with create_test_client(lifespan=[lifespan_manager]):
        assert startup_mock.call_count == 1
        assert shutdown_mock.call_count == 0

    assert shutdown_mock.call_count == 1


def test_lifespan_context_manager_with_hooks(
    lifespan_manager: LifeSpanManager, startup_mock: AsyncMock, shutdown_mock: AsyncMock
) -> None:
    on_startup = AsyncMock()
    on_shutdown = AsyncMock()

    with create_test_client(lifespan=[lifespan_manager], on_startup=[on_startup], on_shutdown=[on_shutdown]):
        assert startup_mock.call_count == 1
        assert on_startup.call_count == 1
        assert shutdown_mock.call_count == 0
        assert on_shutdown.call_count == 0

    assert shutdown_mock.call_count == 1
    assert on_shutdown.call_count == 1


def test_multiple_lifespan_managers() -> None:
    managers: list[LifeSpanManager] = []
    startup_mocks: list[AsyncMock] = []
    shutdown_mocks: list[AsyncMock] = []
    for _ in range(3):
        startup_mock = AsyncMock()
        shutdown_mock = AsyncMock()
        managers.append(create_lifespan_manager(startup_mock, shutdown_mock))
        startup_mocks.append(startup_mock)
        shutdown_mocks.append(shutdown_mock)

    with create_test_client(lifespan=managers):
        assert all(m.call_count == 1 for m in startup_mocks)
        assert all(m.call_count == 0 for m in shutdown_mocks)

    assert all(m.call_count == 1 for m in startup_mocks)
    assert all(m.call_count == 1 for m in shutdown_mocks)
