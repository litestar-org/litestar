from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from litestar.types import Empty
from litestar.utils import (
    delete_litestar_scope_state,
    get_litestar_scope_state,
)

from .common import SESSION_SCOPE_KEY, SESSION_TERMINUS_ASGI_EVENTS, GenericSessionConfig, GenericSQLAlchemyConfig

if TYPE_CHECKING:
    from typing import Any, Callable

    from sqlalchemy.orm import Session

    from litestar.datastructures.state import State
    from litestar.types import BeforeMessageSendHookHandler, EmptyType, Message, Scope

__all__ = ("SQLAlchemyAsyncConfig", "AsyncSessionConfig")


async def default_before_send_handler(message: Message, _: State, scope: Scope) -> None:
    """Handle closing and cleaning up sessions before sending.

    Args:
        message: ASGI-``Message``
        _: A ``State`` (not used)
        scope: An ASGI-``Scope``

    Returns:
        None
    """
    session = cast("AsyncSession | None", get_litestar_scope_state(scope, SESSION_SCOPE_KEY))
    if session and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
        await session.close()
        delete_litestar_scope_state(scope, SESSION_SCOPE_KEY)


@dataclass
class AsyncSessionConfig(GenericSessionConfig[AsyncConnection, AsyncEngine, AsyncSession]):
    """SQLAlchemy async session config."""

    sync_session_class: type[Session] | None | EmptyType = Empty
    """A :class:`Session <sqlalchemy.orm.Session>` subclass or other callable which will be used to construct the
    :class:`Session <sqlalchemy.orm.Session>` which will be proxied. This parameter may be used to provide custom
    :class:`Session <sqlalchemy.orm.Session>` subclasses. Defaults to the
    :attr:`AsyncSession.sync_session_class <sqlalchemy.ext.asyncio.AsyncSession.sync_session_class>` class-level
    attribute."""


@dataclass
class SQLAlchemyAsyncConfig(GenericSQLAlchemyConfig[AsyncEngine, AsyncSession, async_sessionmaker]):
    """Async SQLAlchemy Configuration."""

    create_engine_callable: Callable[[str], AsyncEngine] = create_async_engine
    """Callable that creates an :class:`AsyncEngine <sqlalchemy.ext.asyncio.AsyncEngine>` instance or instance of its
    subclass.
    """
    session_config: AsyncSessionConfig = field(default_factory=AsyncSessionConfig)
    """Configuration options for the :class:`async_sessionmaker<sqlalchemy.ext.asyncio.async_sessionmaker>`."""
    session_maker_class: type[async_sessionmaker] = async_sessionmaker
    """Sessionmaker class to use."""
    before_send_handler: BeforeMessageSendHookHandler = default_before_send_handler
    """Handler to call before the ASGI message is sent.

    The handler should handle closing the session stored in the ASGI scope, if it's still open, and committing and
    uncommitted data.
    """

    @property
    def signature_namespace(self) -> dict[str, Any]:
        """Return the plugin's signature namespace.

        Returns:
            A string keyed dict of names to be added to the namespace for signature forward reference resolution.
        """
        return {"AsyncEngine": AsyncEngine, "AsyncSession": AsyncSession}

    async def on_shutdown(self, state: State) -> None:
        """Disposes of the SQLAlchemy engine.

        Args:
            state: The ``Litestar.state`` instance.

        Returns:
            None
        """
        engine = cast("AsyncEngine", state.pop(self.engine_app_state_key))
        await engine.dispose()
