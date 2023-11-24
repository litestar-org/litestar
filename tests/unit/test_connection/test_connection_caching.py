from __future__ import annotations

from typing import Any, Awaitable, Callable
from unittest.mock import ANY, MagicMock, call

import pytest

from litestar import Request, constants
from litestar.testing import RequestFactory
from litestar.types import Empty, HTTPReceiveMessage, Scope
from litestar.types.scope import ScopeStateKeyType
from litestar.utils import get_litestar_scope_state, set_litestar_scope_state


async def test_multiple_request_object_data_caching(create_scope: Callable[..., Scope], mock: MagicMock) -> None:
    """Test that accessing the request data on multiple request objects only attempts to await `receive()` once.

    https://github.com/litestar-org/litestar/issues/2727
    """

    async def test_receive() -> HTTPReceiveMessage:
        mock()
        return {"type": "http.request", "body": b"abc", "more_body": False}

    scope = create_scope()
    request_1 = Request[Any, Any, Any](scope, test_receive)
    request_2 = Request[Any, Any, Any](scope, test_receive)
    assert (await request_1.body()) == b"abc"
    assert (await request_2.body()) == b"abc"
    assert mock.call_count == 1


@pytest.fixture(name="get_mock")
def get_mock_fixture() -> MagicMock:
    return MagicMock()


@pytest.fixture(name="set_mock")
def set_mock_fixture() -> MagicMock:
    return MagicMock()


@pytest.fixture(name="create_connection")
def create_connection_fixture(
    get_mock: MagicMock, set_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> Callable[..., Request]:
    def create_connection(body_type: str = "json") -> Request:
        def wrapped_get_litestar_scope_state(scope_: Scope, key: ScopeStateKeyType, default: Any = None) -> Any:
            get_mock(key)
            return get_litestar_scope_state(scope_, key, default)

        def wrapped_set_litestar_scope_state(scope_: Scope, key: ScopeStateKeyType, value: Any) -> None:
            set_mock(key, value)
            set_litestar_scope_state(scope_, key, value)

        monkeypatch.setattr("litestar.connection.base.get_litestar_scope_state", wrapped_get_litestar_scope_state)
        monkeypatch.setattr("litestar.connection.base.set_litestar_scope_state", wrapped_set_litestar_scope_state)
        monkeypatch.setattr("litestar.connection.request.get_litestar_scope_state", wrapped_get_litestar_scope_state)
        monkeypatch.setattr("litestar.connection.request.set_litestar_scope_state", wrapped_set_litestar_scope_state)

        connection = RequestFactory().get()

        async def fake_receive() -> HTTPReceiveMessage:
            if body_type == "msgpack":
                return {"type": "http.request", "body": b"\x81\xa3abc\xa3def", "more_body": False}
            return {"type": "http.request", "body": b'{"abc":"def"}', "more_body": False}

        monkeypatch.setattr(connection, "receive", fake_receive)

        return connection

    return create_connection


@pytest.fixture(name="get_value")
def get_value_fixture() -> Callable[[Request, str, bool], Awaitable[Any]]:
    """Fixture to get the value of a connection cached property.

    Returns:
        A function to get the value of a connection cached property.
    """

    async def get_value_(connection: Request, prop_name: str, is_coro: bool) -> Any:
        """Helper to get the value of the tested cached property."""
        value = getattr(connection, prop_name)
        return await value() if is_coro else value

    return get_value_


caching_tests = [
    (constants.SCOPE_STATE_URL_KEY, "url", "_url", False),
    (constants.SCOPE_STATE_BASE_URL_KEY, "base_url", "_base_url", False),
    (
        constants.SCOPE_STATE_PARSED_QUERY_KEY,
        "query_params",
        "_parsed_query",
        False,
    ),
    (constants.SCOPE_STATE_COOKIES_KEY, "cookies", "_cookies", False),
    (constants.SCOPE_STATE_BODY_KEY, "body", "_body", True),
    (constants.SCOPE_STATE_FORM_KEY, "form", "_form", True),
    (constants.SCOPE_STATE_MSGPACK_KEY, "msgpack", "_msgpack", True),
    (constants.SCOPE_STATE_JSON_KEY, "json", "_json", True),
    (constants.SCOPE_STATE_ACCEPT_KEY, "accept", "_accept", False),
    (constants.SCOPE_STATE_CONTENT_TYPE_KEY, "content_type", "_content_type", False),
]


@pytest.mark.parametrize(("state_key", "prop_name", "cache_attr_name", "is_coro"), caching_tests)
async def test_connection_cached_properties_no_scope_or_connection_caching(
    state_key: ScopeStateKeyType,
    prop_name: str,
    cache_attr_name: str,
    is_coro: bool,
    create_connection: Callable[..., Request],
    get_mock: MagicMock,
    set_mock: MagicMock,
    get_value: Callable[[Request, str, bool], Awaitable[Any]],
) -> None:
    def check_get_mock() -> None:
        """Helper to check the get mock.

        For certain properties, we call `get_litestar_scope_state()` twice, once for the property and once for the
        body. For these cases, we check that the mock was called twice.
        """
        if state_key in ("json", "msgpack"):
            get_mock.assert_has_calls([call(state_key), call("body")])
        elif state_key == "form":
            get_mock.assert_has_calls([call(state_key), call("content_type")])
        else:
            get_mock.assert_called_once_with(state_key)

    def check_set_mock() -> None:
        """Helper to check the set mock.

        For certain properties, we call `set_litestar_scope_state()` twice, once for the property and once for the
        body. For these cases, we check that the mock was called twice.
        """
        if state_key in ("json", "msgpack"):
            set_mock.assert_has_calls([call("body", ANY), call(state_key, ANY)])
        elif state_key == "form":
            set_mock.assert_has_calls([call("content_type", ANY), call("form", ANY)])
        else:
            set_mock.assert_called_once_with(state_key, ANY)

    connection = create_connection("msgpack" if state_key == "msgpack" else "json")

    assert get_litestar_scope_state(connection.scope, state_key, Empty) is Empty
    setattr(connection, cache_attr_name, Empty)

    await get_value(connection, prop_name, is_coro)
    check_get_mock()
    check_set_mock()


@pytest.mark.parametrize(("state_key", "prop_name", "cache_attr_name", "is_coro"), caching_tests)
async def test_connection_cached_properties_cached_in_scope(
    state_key: ScopeStateKeyType,
    prop_name: str,
    cache_attr_name: str,
    is_coro: bool,
    create_connection: Callable[..., Request],
    get_mock: MagicMock,
    set_mock: MagicMock,
    get_value: Callable[[Request, str, bool], Awaitable[Any]],
) -> None:
    # set the value in the scope and ensure empty on connection
    connection = create_connection()

    set_litestar_scope_state(connection.scope, state_key, {"a": "b"})  # type: ignore[arg-type]
    setattr(connection, cache_attr_name, Empty)

    await get_value(connection, prop_name, is_coro)
    get_mock.assert_called_once_with(state_key)
    set_mock.assert_not_called()


@pytest.mark.parametrize(("state_key", "prop_name", "cache_attr_name", "is_coro"), caching_tests)
async def test_connection_cached_properties_cached_on_connection(
    state_key: str,
    prop_name: str,
    cache_attr_name: str,
    is_coro: bool,
    create_connection: Callable[..., Request],
    get_mock: MagicMock,
    set_mock: MagicMock,
    get_value: Callable[[Request, str, bool], Awaitable[Any]],
) -> None:
    connection = create_connection()
    # set the value on the connection
    setattr(connection, cache_attr_name, {"a": "b"})
    await get_value(connection, prop_name, is_coro)
    get_mock.assert_not_called()
    set_mock.assert_not_called()
