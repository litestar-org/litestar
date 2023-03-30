from typing import Any, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from starlite import Starlite, get
from starlite.contrib.sqlalchemy_1.config import (
    SESSION_SCOPE_KEY,
    SESSION_TERMINUS_ASGI_EVENTS,
    SQLAlchemyConfig,
    SQLAlchemyEngineConfig,
    serializer,
)
from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.exceptions import ImproperlyConfiguredException
from starlite.logging.config import LoggingConfig
from starlite.status_codes import HTTP_200_OK
from starlite.testing import RequestFactory, create_test_client
from starlite.types import Scope


@pytest.mark.parametrize("connection_string", ["sqlite+aiosqlite://", "sqlite://"])
def test_sets_engine_and_session_maker(connection_string: str) -> None:
    config = SQLAlchemyConfig(connection_string=connection_string, use_async_engine="+aiosqlite" in connection_string)
    with create_test_client([], plugins=[SQLAlchemyPlugin(config=config)]) as client:
        assert client.app.state.get(config.engine_app_state_key)
        assert client.app.state.get(config.session_maker_app_state_key)


@pytest.mark.parametrize("connection_string", ["sqlite+aiosqlite://", "sqlite://"])
def test_dependency_creates_session(connection_string: str) -> None:
    config = SQLAlchemyConfig(connection_string=connection_string, use_async_engine="+aiosqlite" in connection_string)
    with create_test_client([], plugins=[SQLAlchemyPlugin(config=config)]) as client:
        request = RequestFactory().get()
        session = config.create_db_session_dependency(state=client.app.state, scope=request.scope)
    assert session
    assert request.scope[SESSION_SCOPE_KEY]  # type: ignore


@pytest.mark.parametrize("connection_string", ["sqlite+aiosqlite://", "sqlite://"])
def test_on_shutdown(connection_string: str) -> None:
    config = SQLAlchemyConfig(connection_string=connection_string, use_async_engine="+aiosqlite" in connection_string)
    with create_test_client([], plugins=[SQLAlchemyPlugin(config=config)]) as client:
        assert client.app.state.get(config.engine_app_state_key)
    assert not client.app.state.get(config.engine_app_state_key)


@pytest.mark.parametrize(
    "asgi_event_type, connection_string", zip(SESSION_TERMINUS_ASGI_EVENTS, ["sqlite+aiosqlite://", "sqlite://"])
)
def test_session_close(asgi_event_type: str, connection_string: str) -> None:
    request_scope: Any = None
    expected_type = AsyncSession if "+aiosqlite" in connection_string else Session

    @get("/")
    def handler(db_session: expected_type, scope: Scope) -> None:  # type: ignore
        nonlocal request_scope
        assert scope.get(SESSION_SCOPE_KEY) is db_session
        request_scope = scope

    config = SQLAlchemyConfig(connection_string=connection_string, use_async_engine="+aiosqlite" in connection_string)
    with create_test_client([handler], plugins=[SQLAlchemyPlugin(config=config)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert isinstance(request_scope, dict)
        assert not request_scope.get(SESSION_SCOPE_KEY)


def test_engine_supports_json_flag() -> None:
    config = SQLAlchemyConfig(connection_string="sqlite://")
    assert "json_serializer" in config.engine_config_dict
    assert "json_deserializer" in config.engine_config_dict
    config = SQLAlchemyConfig(connection_string="sqlite://", set_json_serializers=False)
    assert "json_serializer" not in config.engine_config_dict
    assert "json_deserializer" not in config.engine_config_dict


@pytest.mark.parametrize(
    "engine_logger, pool_logger, logging_level", [[None, None, None], ["my_engine", "my_pool", "INFO"]]
)
def test_logging_config(engine_logger: Optional[str], pool_logger: Optional[str], logging_level: Optional[str]) -> None:
    config = SQLAlchemyConfig(
        connection_string="sqlite://",
        use_async_engine=False,
        engine_config=SQLAlchemyEngineConfig(
            logging_name=engine_logger, pool_logging_name=pool_logger, logging_level=logging_level
        ),
    )
    logging_config = LoggingConfig()
    app = Starlite(plugins=[SQLAlchemyPlugin(config=config)], logging_config=logging_config)
    assert app.logging_config.loggers[engine_logger or "sqlalchemy.engine"] == {  # type: ignore
        "level": logging_level or "WARNING",
        "handlers": ["queue_listener"],
    }
    assert app.logging_config.loggers[pool_logger or "sqlalchemy.pool"] == {  # type: ignore
        "level": logging_level or "WARNING",
        "handlers": ["queue_listener"],
    }


def test_default_serializer_returns_string() -> None:
    assert serializer({"hello": "world"}) == '{"hello":"world"}'


def test_config_connection_string_or_engine_instance_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        SQLAlchemyConfig(connection_string=None, engine_instance=None)

    connection_string = "sqlite:///"
    engine = create_engine(connection_string)

    with pytest.raises(ImproperlyConfiguredException):
        SQLAlchemyConfig(connection_string=connection_string, engine_instance=engine)

    # these should be OK
    SQLAlchemyConfig(engine_instance=engine)
    SQLAlchemyConfig(connection_string=connection_string)


def test_config_session_maker_class_protocol() -> None:
    """Tests that pydantic allows the type, but also relies on mypy checking that `sessionmaker` conforms to the
    protocol.
    """
    SQLAlchemyConfig(connection_string="sqlite:///", session_maker_class=sessionmaker)


def test_config_session_maker_instance_protocol() -> None:
    """Tests that pydantic allows the type, but also relies on mypy checking that `sessionmaker` conforms to the
    protocol.
    """
    SQLAlchemyConfig(connection_string="sqlite:///", session_maker_instance=sessionmaker())
    # instance can be any callable that returns a session type instance
    SQLAlchemyConfig(connection_string="sqlite:///", session_maker_instance=Session)
    SQLAlchemyConfig(connection_string="sqlite:///", session_maker_instance=AsyncSession)
