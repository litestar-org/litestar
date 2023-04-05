from __future__ import annotations

from typing import TYPE_CHECKING

from starlite import get
from starlite.contrib.sqlalchemy.init_plugin import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from typing import Any

    from sqlalchemy.ext.asyncio import AsyncSession

    from starlite.types import Scope


def test_default_before_send_handler() -> None:
    """Test default_before_send_handler."""

    captured_scope_state: dict[str, Any] | None = None
    config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite://")
    plugin = SQLAlchemyInitPlugin(config=config)

    @get()
    def test_handler(db_session: AsyncSession, scope: Scope) -> None:
        nonlocal captured_scope_state
        captured_scope_state = scope["state"]
        assert db_session is captured_scope_state[config.session_dependency_key]

    with create_test_client(route_handlers=[test_handler], plugins=[plugin]) as client:
        client.get("/")
        assert captured_scope_state is not None
        assert config.session_dependency_key not in captured_scope_state  # pyright: ignore
