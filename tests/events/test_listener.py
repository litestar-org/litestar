from typing import Any, Dict, Optional

import pytest

from starlite import Request, Starlite, get
from starlite.events.listener import listener
from starlite.exceptions import ImproperlyConfiguredException
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client
from starlite.testing.create_test_client import create_async_test_client


def test_event_listener_works_for_sync_callable() -> None:
    test_value = {"key": "123"}
    received_event: Optional[Dict[str, Any]] = None

    @listener("test_event")
    def event_handler(event: Dict[str, Any]) -> None:
        nonlocal received_event
        received_event = event

    @get("/")
    async def route_handler(request: Request[Any, Any, Any]) -> None:
        await request.app.emit("test_event", test_value)

    with create_test_client(route_handlers=[route_handler], listeners=[event_handler]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert received_event == test_value


def test_event_listener_works_for_async_callable() -> None:
    test_value = {"key": "123"}
    received_event: Optional[Dict[str, Any]] = None

    @listener("test_event")
    async def event_handler(event: Dict[str, Any]) -> None:
        nonlocal received_event
        received_event = event

    @get("/")
    async def route_handler(request: Request[Any, Any, Any]) -> None:
        await request.app.emit("test_event", test_value)

    with create_test_client(route_handlers=[route_handler], listeners=[event_handler]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert received_event == test_value


async def test_multiple_event_listeners() -> None:
    received_events: int = 0

    @listener("test_event")
    def sync_event_handler() -> None:
        nonlocal received_events
        received_events += 1

    @listener("test_event")
    async def async_event_handler() -> None:
        nonlocal received_events
        received_events += 1

    @get("/")
    async def route_handler(request: Request[Any, Any, Any]) -> None:
        await request.app.emit("test_event")

    async with create_async_test_client(
        route_handlers=[route_handler], listeners=[sync_event_handler, async_event_handler]
    ) as client:
        response = await client.get("/")
        assert response.status_code == HTTP_200_OK
        assert received_events == 2


def test_raises_when_decorator_called_without_callable() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        listener("test_even")(True)  # type: ignore


async def test_raises_when_no_event_listener_is_registered() -> None:
    app = Starlite([])

    with pytest.raises(ImproperlyConfiguredException):
        await app.emit("x")
