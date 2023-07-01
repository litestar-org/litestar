from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from litestar import Litestar, post
from litestar.contrib.sqlalchemy.plugins import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin

if TYPE_CHECKING:
    from typing import Tuple

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@post("/")
async def handler(db_session: AsyncSession, db_engine: AsyncEngine) -> Tuple[int, int]:
    one = (await db_session.execute(select(1))).scalar()

    async with db_engine.begin() as conn:
        two = (await conn.execute(select(2))).scalar()

    return one, two


config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///async.sqlite")
plugin = SQLAlchemyInitPlugin(config=config)
app = Litestar(route_handlers=[handler], plugins=[plugin])
