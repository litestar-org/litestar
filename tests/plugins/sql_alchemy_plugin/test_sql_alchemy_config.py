from starlite import Starlite
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from starlite.plugins.sql_alchemy.config import SQLAlchemyConfig
from starlite.testing import RequestFactory, create_test_client


def test_sets_engine_and_session_maker() -> None:
    config = SQLAlchemyConfig(connection_string="sqlite+aiosqlite://")
    app = Starlite(route_handlers=[], plugins=[SQLAlchemyPlugin(config=config)])
    assert app.state.get(config.engine_app_state_key)
    assert app.state.get(config.session_maker_app_state_key)


def test_dependency_creates_session() -> None:
    config = SQLAlchemyConfig(connection_string="sqlite+aiosqlite://")
    app = Starlite(route_handlers=[], plugins=[SQLAlchemyPlugin(config=config)])
    request = RequestFactory().get("/")
    session = config.create_db_session_dependency(state=app.state, scope=request.scope)
    assert session
    assert request.scope[config.session_scope_key]  # type: ignore


def test_on_shutdown() -> None:
    config = SQLAlchemyConfig(connection_string="sqlite+aiosqlite://")
    with create_test_client([], plugins=[SQLAlchemyPlugin(config=config)]) as client:
        assert client.app.state.get(config.engine_app_state_key)
    assert not client.app.state.get(config.engine_app_state_key)
