from __future__ import annotations

from typing import TYPE_CHECKING


from advanced_alchemy.extensions.litestar.plugins.init.config.common import (
    SESSION_SCOPE_KEY,
    SESSION_TERMINUS_ASGI_EVENTS,
)
from advanced_alchemy.config.common import GenericAlembicConfig, GenericSessionConfig, GenericSQLAlchemyConfig

if TYPE_CHECKING:
    from typing import Any

    from sqlalchemy import Connection, Engine
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import Mapper, Query, Session, sessionmaker
    from sqlalchemy.orm.session import JoinTransactionMode
    from sqlalchemy.sql import TableClause

    from litestar import Litestar
    from litestar.datastructures.state import State
    from litestar.types import BeforeMessageSendHookHandler, EmptyType, Scope

__all__ = (
    "SESSION_SCOPE_KEY",
    "SESSION_TERMINUS_ASGI_EVENTS",
    "GenericSQLAlchemyConfig",
    "GenericSessionConfig",
    "GenericAlembicConfig",
)
