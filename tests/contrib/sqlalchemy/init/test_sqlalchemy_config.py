from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from starlite import Starlite, get
from starlite.contrib.sqlalchemy.init import SQLAlchemyInit
from starlite.contrib.sqlalchemy.init.config import (
    SESSION_SCOPE_KEY,
    SESSION_TERMINUS_ASGI_EVENTS,
    SQLAlchemyConfig,
    serializer,
)
from starlite.exceptions import ImproperlyConfiguredException
from starlite.status_codes import HTTP_200_OK
from starlite.testing import RequestFactory, create_test_client
from starlite.types import Scope
from starlite.utils import get_starlite_scope_state

CONN_STR = "sqlite+aiosqlite:///"


@pytest.fixture(name="config")
def fx_config() -> SQLAlchemyConfig:
    return SQLAlchemyConfig(connection_string=CONN_STR)


def test_sets_engine_and_session_maker(config: SQLAlchemyConfig) -> None:
    app = Starlite(on_app_init=[SQLAlchemyInit(config)])
    assert app.state.get(config.engine_app_state_key)
    assert app.state.get(config.session_maker_app_state_key)


def test_dependency_creates_session(config: SQLAlchemyConfig) -> None:
    app = Starlite(on_app_init=[SQLAlchemyInit(config)])
    request = RequestFactory().get()
    session = config.create_db_session_dependency(state=app.state, scope=request.scope)
    assert session
    assert get_starlite_scope_state(request.scope, SESSION_SCOPE_KEY)


def test_on_shutdown(config: SQLAlchemyConfig) -> None:
    with create_test_client([], on_app_init=[SQLAlchemyInit(config)]) as client:
        assert client.app.state.get(config.engine_app_state_key)
    assert not client.app.state.get(config.engine_app_state_key)


@pytest.mark.parametrize("asgi_event_type", SESSION_TERMINUS_ASGI_EVENTS)
def test_session_close(asgi_event_type: str, config: SQLAlchemyConfig) -> None:
    request_scope: Any = None

    @get("/")
    def handler(db_session: AsyncSession, scope: Scope) -> None:
        nonlocal request_scope
        assert get_starlite_scope_state(scope, SESSION_SCOPE_KEY) is db_session
        request_scope = scope

    with create_test_client([handler], on_app_init=[SQLAlchemyInit(config)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert isinstance(request_scope, dict)
        assert not get_starlite_scope_state(request_scope, SESSION_SCOPE_KEY)  # type:ignore[arg-type]


def test_default_serializer_returns_string() -> None:
    assert serializer({"hello": "world"}) == '{"hello":"world"}'


def test_config_connection_string_or_engine_instance_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        SQLAlchemyConfig(connection_string=None, engine_instance=None)

    engine = create_async_engine(CONN_STR)

    with pytest.raises(ImproperlyConfiguredException):
        SQLAlchemyConfig(connection_string=CONN_STR, engine_instance=engine)

    # these should be OK
    SQLAlchemyConfig(engine_instance=engine)
    SQLAlchemyConfig(connection_string=CONN_STR)
