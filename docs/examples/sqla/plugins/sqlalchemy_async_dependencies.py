from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin
from litestar.plugins.sqlalchemy import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin
from sqlalchemy import select

from litestar import Litestar, post
from litestar.di import NamedDependency

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@post("/")
async def handler(
    db_session: NamedDependency[AsyncSession], db_engine: NamedDependency[AsyncEngine]
) -> tuple[int, int]:
    one = (await db_session.execute(select(1))).scalar()

    async with db_engine.begin() as conn:
        two = (await conn.execute(select(2))).scalar()

    return one, two


config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///async.sqlite")
plugin = SQLAlchemyInitPlugin(config=config)
app = Litestar(route_handlers=[handler], plugins=[plugin])
