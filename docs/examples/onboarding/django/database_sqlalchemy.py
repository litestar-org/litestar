from collections.abc import Sequence
from typing import Annotated

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, get, post
from litestar.dto import DTOConfig
from litestar.plugins.sqlalchemy import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyDTO,
    SQLAlchemyPlugin,
)


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "migration_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]


WriteItemDTO = SQLAlchemyDTO[Annotated[Item, DTOConfig(exclude={"id"})]]
ReadItemDTO = SQLAlchemyDTO[Item]


@post("/items", dto=WriteItemDTO, return_dto=ReadItemDTO)
async def create_item(data: Item, db_session: AsyncSession) -> Item:
    async with db_session.begin():
        db_session.add(data)
    return data


@get("/items", return_dto=ReadItemDTO)
async def list_items(db_session: AsyncSession) -> Sequence[Item]:
    return (await db_session.execute(select(Item))).scalars().all()


config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:",
    create_all=True,
    metadata=Base.metadata,
    session_config=AsyncSessionConfig(expire_on_commit=False),
)
app = Litestar(
    route_handlers=[create_item, list_items],
    plugins=[SQLAlchemyPlugin(config=config)],
)
