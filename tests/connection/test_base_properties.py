from typing import Any

from litestar import Litestar, get
from litestar.connection import ASGIConnection
from litestar.logging.config import LoggingConfig
from litestar.testing import RequestFactory


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
    assert connection.user is user
    assert connection.auth is auth
    assert connection.session is session
