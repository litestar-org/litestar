from asyncio import sleep
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_lazyfixture import lazy_fixture

from starlite import Request, Starlite, get
from starlite.events.emitter import SimpleEventEmitter
from starlite.events.listener import EventListener, listener
from starlite.exceptions import ImproperlyConfiguredException
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_async_test_client, create_test_client


@pytest.fixture()
def mock() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def sync_listener(mock: MagicMock) -> EventListener:
    @listener("test_event")
    def listener_fn(*args: Any, **kwargs: Any) -> None:
        mock(*args, **kwargs)

    return listener_fn


@pytest.fixture()
def async_listener(mock: MagicMock) -> EventListener:
    @listener("test_event")
    async def listener_fn(*args: Any, **kwargs: Any) -> None:
        mock(*args, **kwargs)

    return listener_fn


@pytest.mark.parametrize("listener", [lazy_fixture("sync_listener"), lazy_fixture("async_listener")])
async def test_event_listener(mock: MagicMock, listener: EventListener) -> None:
    test_value = {"key": "123"}

    @get("/")
    async def route_handler(request: Request[Any, Any, Any]) -> None:
        await request.app.emit("test_event", test_value)

    with create_test_client(route_handlers=[route_handler], listeners=[listener]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        await sleep(0.01)
        mock.assert_called_with(test_value)


async def test_shutdown_awaits_pending(async_listener: EventListener, mock: MagicMock) -> None:
    emitter = SimpleEventEmitter([async_listener])
    await emitter.on_startup()

    for _ in range(100):
        await emitter.emit("test_event")

    await emitter.on_shutdown()

    assert mock.call_count == 100


async def test_multiple_event_listeners(
    async_listener: EventListener, sync_listener: EventListener, mock: MagicMock
) -> None:
    @get("/")
    async def route_handler(request: Request[Any, Any, Any]) -> None:
        await request.app.emit("test_event")

    async with create_async_test_client(
        route_handlers=[route_handler], listeners=[async_listener, sync_listener]
    ) as client:
        response = await client.get("/")
        await sleep(0.01)
        assert response.status_code == HTTP_200_OK
        assert mock.call_count == 2


async def test_multiple_event_ids(mock: MagicMock) -> None:
    @listener("test_event_1", "test_event_2")
    def event_handler() -> None:
        mock()

    @get("/{event_id:int}")
    async def route_handler(request: Request[Any, Any, Any], event_id: int) -> None:
        await request.app.emit(f"test_event_{event_id}")

    async with create_async_test_client(route_handlers=[route_handler], listeners=[event_handler]) as client:
        response = await client.get("/1")
        await sleep(0.01)
        assert response.status_code == HTTP_200_OK
        assert mock.call_count == 1
        response = await client.get("/2")
        await sleep(0.01)
        assert response.status_code == HTTP_200_OK
        assert mock.call_count == 2


def test_raises_when_decorator_called_without_callable() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        listener("test_even")(True)  # type: ignore


async def test_raises_when_not_initialized() -> None:
    app = Starlite([])

    with pytest.raises(ImproperlyConfiguredException):
        await app.emit("x")


async def test_raises_when_not_listener_are_registered_for_an_event_id(async_listener: EventListener) -> None:
    async with create_async_test_client(route_handlers=[], listeners=[async_listener]) as client:
        with pytest.raises(ImproperlyConfiguredException):
            await client.app.emit("x")
