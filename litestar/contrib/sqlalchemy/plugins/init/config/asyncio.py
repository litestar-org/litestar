from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from litestar.constants import HTTP_RESPONSE_START
from litestar.types import Empty
from litestar.utils import delete_litestar_scope_state, get_litestar_scope_state

from .common import SESSION_SCOPE_KEY, SESSION_TERMINUS_ASGI_EVENTS, GenericSessionConfig, GenericSQLAlchemyConfig

if TYPE_CHECKING:
    from typing import Any, Callable

    from sqlalchemy.orm import Session

    from litestar import Litestar
    from litestar.types import BeforeMessageSendHookHandler, EmptyType, Message, Scope
    from litestar.types.asgi_types import HTTPResponseStartEvent

__all__ = (
    "SQLAlchemyAsyncConfig",
    "AsyncSessionConfig",
    "default_before_send_handler",
    "autocommit_before_send_handler",
)


async def default_before_send_handler(message: Message, scope: Scope) -> None:
    """Handle closing and cleaning up sessions before sending.

    Args:
        message: ASGI-``Message``
        scope: An ASGI-``Scope``

    Returns:
        None
    """
    session = cast("AsyncSession | None", get_litestar_scope_state(scope, SESSION_SCOPE_KEY))
    if session and message["type"] in SESSION_TERMINUS_ASGI_EVENTS:
        await session.close()
        delete_litestar_scope_state(scope, SESSION_SCOPE_KEY)


async def autocommit_before_send_handler(message: Message, scope: Scope) -> None:
    """Handle commit/rollback, closing and cleaning up sessions before sending.

    Args:
        message: ASGI-``Message``
        scope: An ASGI-``Scope``

    Returns:
        None
    """
    session = cast("AsyncSession | None", get_litestar_scope_state(scope, SESSION_SCOPE_KEY))
    try:
        if session is not None and message["type"] == HTTP_RESPONSE_START:
            if 200 <= cast("HTTPResponseStartEvent", message)["status"] < 300:
                await session.commit()
            else:
                await session.rollback()
    finally:
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

    async def on_shutdown(self, app: Litestar) -> None:
        """Disposes of the SQLAlchemy engine.

        Args:
            app: The ``Litestar`` instance.

        Returns:
            None
        """
        engine = cast("AsyncEngine", app.state.pop(self.engine_app_state_key))
        await engine.dispose()
