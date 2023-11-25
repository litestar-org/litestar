from typing import Any

from litestar import Litestar, get
from litestar.connection import ASGIConnection
from litestar.logging.config import LoggingConfig
from litestar.testing import RequestFactory
from litestar.types.empty import Empty
from litestar.utils.scope.state import ScopeState


def test_connection_base_properties() -> None:
    @get("/")
    def handler() -> None:
        return None

    app = Litestar(route_handlers=[handler], logging_config=LoggingConfig())
    user = {"name": "moishe"}
    auth = {"key": "value"}
    session = {"session": "abc"}
    scope = RequestFactory(app=app).get(route_handler=handler, user=user, auth=auth, session=session).scope
    connection = ASGIConnection[Any, Any, Any, Any](scope)
    connection_state = ScopeState.from_scope(scope)

    assert connection.app
    assert connection.app is app
    assert connection.route_handler is handler
    assert connection.state is not None
    assert connection_state.url is Empty
    assert connection.url
    assert connection_state.url is not Empty
    assert connection_state.base_url is Empty  # type:ignore[unreachable]
    assert connection.base_url
    assert connection_state.base_url is not Empty
    assert connection_state.headers is Empty
    assert connection.headers is not None
    assert connection_state.headers is not Empty
    assert connection_state.parsed_query is Empty
    assert connection.query_params is not None
    assert connection_state.parsed_query is not Empty
    assert connection_state.cookies is Empty
    assert connection.cookies is not None
    assert connection_state.cookies is not Empty
    assert connection.client
    assert connection.user is user
    assert connection.auth is auth
    assert connection.session is session
