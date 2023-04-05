from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from litestar.utils import (
    delete_litestar_scope_state,
    get_litestar_scope_state,
)

from .common import SESSION_SCOPE_KEY, SESSION_TERMINUS_ASGI_EVENTS, GenericSessionConfig, GenericSQLAlchemyConfig

if TYPE_CHECKING:
    from typing import Any, Callable

    from litestar.datastructures.state import State
    from litestar.types import BeforeMessageSendHookHandler, Message, Scope

__all__ = ("SQLAlchemySyncConfig", "SyncSessionConfig")


async def default_before_send_handler(message: Message, _: State, scope: Scope) -> None:
    """Handle closing and cleaning up sessions before sending.

    Args:
        message: ASGI-``Message``
        _: A ``State`` (not used)
        scope: An ASGI-``Scope``

    Returns:
        None
    """
    session = cast("Session | None", get_litestar_scope_state(scope, SESSION_SCOPE_KEY))
    if session and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
        session.close()
        delete_litestar_scope_state(scope, SESSION_SCOPE_KEY)


class SyncSessionConfig(GenericSessionConfig[Connection, Engine, Session]):
    pass


@dataclass
class SQLAlchemySyncConfig(GenericSQLAlchemyConfig[Engine, Session, sessionmaker]):
    """Sync SQLAlchemy Configuration."""

    create_engine_callable: Callable[[str], Engine] = create_engine
    """Callable that creates an :class:`AsyncEngine <sqlalchemy.ext.asyncio.AsyncEngine>` instance or instance of its
    subclass.
    """
    session_config: SyncSessionConfig = field(default_factory=SyncSessionConfig)  # pyright:ignore
    """Configuration options for the :class:`sessionmaker<sqlalchemy.orm.sessionmaker>`."""
    session_maker_class: type[sessionmaker] = sessionmaker
    """Sessionmaker class to use."""
    before_send_handler: BeforeMessageSendHookHandler = default_before_send_handler
    """Handler to call before the ASGI message is sent.

    The handler should handle closing the session stored in the ASGI scope, if its still open, and committing and
    uncommitted data.
    """

    @property
    def signature_namespace(self) -> dict[str, Any]:
        """Return the plugin's signature namespace.

        Returns:
            A string keyed dict of names to be added to the namespace for signature forward reference resolution.
        """
        return {"Engine": Engine, "Session": Session}

    def on_shutdown(self, state: State) -> None:
        """Disposes of the SQLAlchemy engine.

        Args:
            state: The ``Litestar.state`` instance.

        Returns:
            None
        """
        engine = cast("Engine", state.pop(self.engine_app_state_key))
        engine.dispose()
