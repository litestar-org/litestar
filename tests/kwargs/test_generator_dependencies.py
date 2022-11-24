from typing import AsyncGenerator, Callable, Dict, Generator
from unittest.mock import MagicMock

import pytest
from pytest import FixtureRequest
from starlette.responses import JSONResponse

from starlite import Provide, create_test_client, get


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
def generator_dependency(
    cleanup_mock: MagicMock, exception_mock: MagicMock, finally_mock: MagicMock
) -> Callable[[], Generator[str, None, None]]:
    def dependency() -> Generator[str, None, None]:
        try:
            yield "hello"
            cleanup_mock()
        except ValueError:
            exception_mock()
        finally:
            finally_mock()

    return dependency


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


@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
def test_generator_dependency(
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)

    @get("/", dependencies={"dep": Provide(dependency)})
    def handler(dep: str) -> Dict[str, str]:
        return {"value": dep}

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"value": "hello"}
        cleanup_mock.assert_called_once()
        finally_mock.assert_called_once()
        exception_mock.assert_not_called()


@pytest.mark.parametrize("dependency_fixture", ["generator_dependency", "async_generator_dependency"])
def test_generator_dependency_handle_exception(
    request: FixtureRequest,
    dependency_fixture: str,
    cleanup_mock: MagicMock,
    exception_mock: MagicMock,
    finally_mock: MagicMock,
) -> None:
    dependency = request.getfixturevalue(dependency_fixture)

    @get("/", dependencies={"dep": Provide(dependency)})
    def handler(dep: str) -> Dict[str, str]:
        raise ValueError("foo")

    with create_test_client(route_handlers=[handler]) as client:
        res = client.get("/")
        assert res.status_code == 500
        assert res.json() == {"detail": "ValueError('foo')", "status_code": 500}
        cleanup_mock.assert_not_called()
        exception_mock.assert_called_once()
        finally_mock.assert_called_once()
