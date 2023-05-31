from __future__ import annotations

import random
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from litestar import Litestar, get
from litestar.contrib.sqlalchemy.plugins import SQLAlchemyInitPlugin, SQLAlchemySyncConfig
from litestar.contrib.sqlalchemy.plugins.init.config.common import SESSION_SCOPE_KEY
from litestar.contrib.sqlalchemy.plugins.init.config.sync import autocommit_before_send_handler
from litestar.testing import create_test_client
from litestar.types.asgi_types import HTTPResponseStartEvent
from litestar.utils import set_litestar_scope_state

if TYPE_CHECKING:
    from typing import Any, Callable

    from litestar.types import Scope


def test_default_before_send_handler() -> None:
    """Test default_before_send_handler."""

    captured_scope_state: dict[str, Any] | None = None
    config = SQLAlchemySyncConfig(connection_string="sqlite+aiosqlite://")
    plugin = SQLAlchemyInitPlugin(config=config)

    @get()
    def test_handler(db_session: Session, scope: Scope) -> None:
        nonlocal captured_scope_state
        captured_scope_state = scope["state"]
        assert db_session is captured_scope_state[config.session_dependency_key]

    with create_test_client(route_handlers=[test_handler], plugins=[plugin]) as client:
        client.get("/")
        assert captured_scope_state is not None
        assert config.session_dependency_key not in captured_scope_state


def test_before_send_handler_success_response(create_scope: Callable[..., Scope]) -> None:
    """Test that the session is committed given a success response."""
    config = SQLAlchemySyncConfig(connection_string="sqlite://", before_send_handler=autocommit_before_send_handler)
    app = Litestar(route_handlers=[], plugins=[SQLAlchemyInitPlugin(config)])
    mock_session = MagicMock(spec=Session)
    http_scope = create_scope(app=app)
    set_litestar_scope_state(http_scope, SESSION_SCOPE_KEY, mock_session)
    http_response_start: HTTPResponseStartEvent = {
        "type": "http.response.start",
        "status": random.randint(200, 299),
        "headers": {},
    }
    autocommit_before_send_handler(http_response_start, http_scope)
    mock_session.commit.assert_called_once()


def test_before_send_handler_error_response(create_scope: Callable[..., Scope]) -> None:
    """Test that the session is committed given a success response."""
    config = SQLAlchemySyncConfig(connection_string="sqlite://", before_send_handler=autocommit_before_send_handler)
    app = Litestar(route_handlers=[], plugins=[SQLAlchemyInitPlugin(config)])
    mock_session = MagicMock(spec=Session)
    http_scope = create_scope(app=app)
    set_litestar_scope_state(http_scope, SESSION_SCOPE_KEY, mock_session)
    http_response_start: HTTPResponseStartEvent = {
        "type": "http.response.start",
        "status": random.randint(300, 599),
        "headers": {},
    }
    autocommit_before_send_handler(http_response_start, http_scope)
    mock_session.rollback.assert_called_once()
