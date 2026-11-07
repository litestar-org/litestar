from __future__ import annotations

from typing import TYPE_CHECKING

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin
from sqlalchemy import literal, select

from litestar import Litestar, post
from litestar.di import NamedDependency

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@post("/")
async def handler(
    db_session: NamedDependency[AsyncSession], db_engine: NamedDependency[AsyncEngine]
) -> tuple[int, int]:
    one = (await db_session.scalars(select(literal(1)))).one()

    async with db_engine.begin() as conn:
        two = (await conn.scalars(select(literal(2)))).one()

    return one, two


config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///async.sqlite")
plugin = SQLAlchemyInitPlugin(config=config)
app = Litestar(route_handlers=[handler], plugins=[plugin])
