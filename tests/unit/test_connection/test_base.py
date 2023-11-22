from typing import Any

from litestar import Litestar, constants, get
from litestar.connection import ASGIConnection
from litestar.logging.config import LoggingConfig
from litestar.testing import RequestFactory
from litestar.utils.scope import get_litestar_scope_state


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

    assert connection.app
    assert connection.app is app
    assert connection.route_handler is handler
    assert connection.state is not None
    assert not get_litestar_scope_state(scope, constants.SCOPE_STATE_URL_KEY)
    assert connection.url
    assert get_litestar_scope_state(scope, constants.SCOPE_STATE_URL_KEY)
    assert not get_litestar_scope_state(scope, constants.SCOPE_STATE_BASE_URL_KEY)
    assert connection.base_url
    assert get_litestar_scope_state(scope, constants.SCOPE_STATE_BASE_URL_KEY)
    assert not scope.get("_headers")
    assert connection.headers is not None
    assert scope.get("_headers") is not None
    assert not get_litestar_scope_state(scope, constants.SCOPE_STATE_PARSED_QUERY_KEY)
    assert connection.query_params is not None
    assert get_litestar_scope_state(scope, constants.SCOPE_STATE_PARSED_QUERY_KEY) is not None
    assert not get_litestar_scope_state(scope, constants.SCOPE_STATE_COOKIES_KEY)
    assert connection.cookies is not None
    assert get_litestar_scope_state(scope, constants.SCOPE_STATE_COOKIES_KEY) is not None
    assert connection.client
    assert connection.user is user
    assert connection.auth is auth
    assert connection.session is session
