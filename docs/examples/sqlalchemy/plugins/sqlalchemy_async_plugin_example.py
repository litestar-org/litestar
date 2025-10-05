from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, post
from litestar.plugins.sqlalchemy import SQLAlchemyAsyncConfig, SQLAlchemyPlugin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Base(DeclarativeBase): ...


class TodoItem(Base):
    __tablename__ = "todo_item"
    title: Mapped[str] = mapped_column(primary_key=True)
    done: Mapped[bool]


@post("/")
async def add_item(data: TodoItem, db_session: AsyncSession) -> Sequence[TodoItem]:
    async with db_session.begin():
        db_session.add(data)
    return (await db_session.execute(select(TodoItem))).scalars().all()


config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///todo_async.sqlite", create_all=True, metadata=Base.metadata
)
plugin = SQLAlchemyPlugin(config=config)
app = Litestar(route_handlers=[add_item], plugins=[plugin])
