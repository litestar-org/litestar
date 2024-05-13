import uuid
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar import Litestar, get
from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.plugins import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyPlugin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


# the SQLAlchemy base includes a declarative model for you to use in your models.
# The `Base` class includes a `UUID` based primary key (`id`)
class Author(UUIDBase):
    name: Mapped[str]
    dob: Mapped[date]
    books: Mapped[list["Book"]] = relationship(back_populates="author", lazy="selectin")


# The `AuditBase` class includes the same UUID` based primary key (`id`) and 2
# additional columns: `created_at` and `updated_at`. `created_at` is a timestamp of when the
# record created, and `updated_at` is the last time the record was modified.
class Book(UUIDAuditBase):
    title: Mapped[str]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True, viewonly=True)


session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config, create_all=True
)  # Create 'async_session' dependency.


async def on_startup() -> None:
    """Initializes the database and adds some dummy data."""
    async with sqlalchemy_config.get_engine().begin() as conn:
        await conn.run_sync(UUIDBase.metadata.create_all)
    async with sqlalchemy_config.get_session() as session:
        statement = select(func.count()).select_from(Author)
        count = await session.execute(statement)
        if 0 == count.scalar():
            author_id = uuid.uuid4()
            session.add(Author(name="Stephen King", dob=date(1954,9,21), id=author_id ))
            session.add(Book(title="It", author_id=author_id))
            await session.commit()


@get(path="/authors")
async def get_authors(db_session: "AsyncSession", db_engine: "AsyncEngine") -> list[Author]:
    """Interact with SQLAlchemy engine and session."""
    return list(await db_session.scalars(select(Author)))


app = Litestar(
    route_handlers=[get_authors],
    on_startup=[on_startup],
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
)
