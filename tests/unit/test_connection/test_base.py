from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from litestar import Litestar, get
from litestar.connection import ASGIConnection
from litestar.constants import SCOPE_SESSION_KEY
from litestar.exceptions import ImproperlyConfiguredException
from litestar.logging.config import LoggingConfig
from litestar.testing import RequestFactory
from litestar.types import Empty, Scope

if TYPE_CHECKING:
    from litestar.handlers import HTTPRouteHandler


@pytest.fixture(name="handler")
def fixture_handler() -> HTTPRouteHandler:
    @get("/")
    def handler() -> None:
        return None

    return handler


@pytest.fixture(name="app")
def fixture_app(handler: HTTPRouteHandler) -> Litestar:
    return Litestar(route_handlers=[handler], logging_config=LoggingConfig())


@pytest.fixture(name="user")
def fixture_user() -> dict[str, str]:
    return {"name": "moishe"}


@pytest.fixture(name="auth")
def fixture_auth() -> dict[str, str]:
    return {"key": "value"}


@pytest.fixture(name="session")
def fixture_session() -> dict[str, str]:
    return {"session": "abc"}


@pytest.fixture(name="scope")
def fixture_scope(
    app: Litestar, handler: HTTPRouteHandler, user: dict[str, Any], auth: dict[str, Any], session: dict[str, Any]
) -> Scope:
    user = {"name": "moishe"}
    auth = {"key": "value"}
    session = {"session": "abc"}
    return RequestFactory(app=app).get(route_handler=handler, user=user, auth=auth, session=session).scope


@pytest.fixture(name="connection")
def fixture_connection(scope: Scope) -> ASGIConnection[Any, Any, Any, Any]:
    return ASGIConnection(scope)


def test_connection_base_properties(
    app: Litestar,
    handler: HTTPRouteHandler,
    user: dict[str, Any],
    auth: dict[str, Any],
    session: dict[str, Any],
    scope: Scope,
    connection: ASGIConnection,
) -> None:
    connection = ASGIConnection[Any, Any, Any, Any](scope)

    assert connection.app
    assert connection.app is app
    assert connection.route_handler is handler
    assert connection.state is not None
    assert not scope.get("_url")
    assert connection.url
    assert scope.get("_url")
    assert not scope.get("_base_url")
    assert connection.base_url
    assert scope.get("_base_url")
    assert not scope.get("_headers")
    assert connection.headers is not None
    assert scope.get("_headers") is not None
    assert not scope.get("_parsed_query")
    assert connection.query_params is not None
    assert scope.get("_parsed_query") is not None
    assert not scope.get("_cookies")
    assert connection.cookies is not None
    assert scope.get("_cookies") is not None
    assert connection.client
    assert connection.user == user
    assert connection.auth == auth
    assert connection.session == session


def test_connection_session_raises_when_unset(connection: ASGIConnection) -> None:
    del connection.scope[SCOPE_SESSION_KEY]  # type: ignore[misc]

    with pytest.raises(ImproperlyConfiguredException):
        connection.session


def test_connection_session_raises_when_is_empty(connection: ASGIConnection) -> None:
    connection.clear_session()
    assert connection.scope[SCOPE_SESSION_KEY] is Empty

    with pytest.raises(ImproperlyConfiguredException):
        connection.session
