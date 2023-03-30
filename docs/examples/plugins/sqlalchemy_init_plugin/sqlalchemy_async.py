from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from starlite import Starlite, get
from starlite.contrib.sqlalchemy.init_plugin import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@get(path="/sqlalchemy-app")
async def async_sqlalchemy_init(db_session: AsyncSession, db_engine: AsyncEngine) -> str:
    """Interact with SQLAlchemy engine and session."""
    one = (await db_session.execute(text("SELECT 1"))).scalar_one()

    async with db_engine.begin() as conn:
        two = (await conn.execute(text("SELECT 2"))).scalar_one()

    return f"{one} {two}"


sqlalchemy_config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///test.sqlite")

app = Starlite(
    route_handlers=[async_sqlalchemy_init],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
)
