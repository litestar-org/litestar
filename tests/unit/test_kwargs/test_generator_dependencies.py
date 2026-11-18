from collections.abc import AsyncGenerator, Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from litestar import Response, WebSocket, get, websocket
from litestar.di import NamedDependency
from litestar.response.base import ASGIResponse
from litestar.testing import create_test_client


@pytest.fixture
def cleanup_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def exception_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def finally_mock() -> MagicMock:
    return MagicMock()


@pytest.fixture
def async_generator_dependency(
    cleanup_mock: MagicMock, exception_mock: MagicMock, finally_mock: MagicMock
) -> Callable[[], AsyncGenerator[str, None]]:
    async def dependency() -> AsyncGenerator[str, None]:
        try:
            yield "hello"
            cleanup_mock()
        except ValueError:
            exception_mock()
        finally:
            finally_mock()

    return dependency


@pytest.mark.parametrize("cache", [False, True])
def test_generator_dependency(
    cache: bool,
    async_generator_dependency: Callable[[], AsyncGenerator[str, None]],
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = async_generator_dependency

    @get("/", dependencies={"dep": dependency}, cache=cache)
    def handler(dep: NamedDependency[str]) -> dict[str, str]:
        return {"value": dep}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"value": "hello"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()
        exception_mock.assert_not_called()


async def test_generator_dependency_websocket(
    async_generator_dependency: Callable[[], AsyncGenerator[str, None]],
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = async_generator_dependency

    @websocket("/ws", dependencies={"dep": dependency})
    async def ws_handler(socket: WebSocket, dep: NamedDependency[str]) -> None:
        await socket.accept()
        await socket.send_json({"value": dep})
        await socket.close()

    with create_test_client(route_handlers=[ws_handler]) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json() == {"value": "hello"}
    cleanup_mock.assert_called_once()
    finally_mock.assert_called_once()
    exception_mock.assert_not_called()


def test_generator_dependency_handle_exception_debug_false(
    async_generator_dependency: Callable[[], AsyncGenerator[str, None]],
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = async_generator_dependency

    @get("/", dependencies={"dep": dependency})
    def handler(dep: NamedDependency[str]) -> dict[str, str]:
        raise ValueError("foo")

    with create_test_client(route_handlers=[handler], debug=False) as client:
        res = client.get("/")

    assert res.status_code == 500
    assert res.text == "500 - Internal Server Error"
    cleanup_mock.assert_not_called()
    exception_mock.assert_called_once()
    finally_mock.assert_called_once()


def test_generator_dependency_exception_during_cleanup_debug_false(
    async_generator_dependency: Callable[[], AsyncGenerator[str, None]],
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = async_generator_dependency
    cleanup_mock.side_effect = Exception("foo")

    @get("/", dependencies={"dep": dependency})
    def handler(dep: NamedDependency[str]) -> dict[str, str]:
        return {"value": dep}

    with create_test_client(route_handlers=[handler], debug=False) as client:
        res = client.get("/")

    assert res.status_code == 500
    assert res.text == "500 - Internal Server Error"
    cleanup_mock.assert_called_once()
    finally_mock.assert_called_once()


@pytest.mark.usefixtures("disable_warn_sync_to_thread_with_async")
def test_generator_dependency_nested(
    async_generator_dependency: Callable[[], AsyncGenerator[str, None]],
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = async_generator_dependency

    async def nested_dependency_one(generator_dep: NamedDependency[str]) -> str:
        return generator_dep

    async def nested_dependency_two(generator_dep: NamedDependency[str], nested_one: NamedDependency[str]) -> str:
        return generator_dep + nested_one

    @get(
        "/",
        dependencies={
            "generator_dep": dependency,
            "nested_one": nested_dependency_one,
            "nested_two": nested_dependency_two,
        },
    )
    def handler(nested_two: NamedDependency[str]) -> dict[str, str]:
        return {"value": nested_two}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"value": "hellohello"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()
        exception_mock.assert_not_called()


def test_generator_dependency_nested_error_during_cleanup(
    async_generator_dependency: Callable[[], AsyncGenerator[str, None]],
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = async_generator_dependency
    cleanup_mock_no_raise = MagicMock()
    cleanup_mock.side_effect = ValueError()

    async def other_dependency(generator_dep: NamedDependency[str]) -> AsyncGenerator[str, None]:
        try:
            yield f"{generator_dep}, world"
        finally:
            cleanup_mock_no_raise()

    @get(
        "/",
        dependencies={"generator_dep": dependency, "other": other_dependency},
    )
    def handler(other: NamedDependency[str]) -> dict[str, str]:
        return {"value": other}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"value": "hello, world"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()
        exception_mock.assert_called_once()
        cleanup_mock_no_raise.assert_called_once()


def test_exception_on_response_thrown_into_generators() -> None:
    counter = 0

    async def dependency() -> AsyncGenerator[int, None]:
        nonlocal counter
        counter += 1
        try:
            yield counter
        finally:
            counter -= 1

    class CustomResponse(Response[str]):
        def to_asgi_response(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> ASGIResponse:
            raise Exception("foo")

    @get("/", dependencies={"dep": dependency})
    def handler(dep: NamedDependency[int]) -> CustomResponse:
        return CustomResponse("")

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 500
        assert counter == 0


def test_exception_thrown_during_cleanup_of_exception() -> None:
    counter = 0

    async def dependency() -> AsyncGenerator[int, None]:
        nonlocal counter
        counter += 1
        try:
            yield counter
        finally:
            counter -= 1
            raise ValueError()

    class CustomResponse(Response[str]):
        def to_asgi_response(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> ASGIResponse:
            raise Exception("foo")

    @get("/", dependencies={"dep": dependency})
    def handler(dep: NamedDependency[int]) -> CustomResponse:
        return CustomResponse("")

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 500
        assert counter == 0
