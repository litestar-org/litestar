from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar import Litestar, get
from litestar.contrib.sqlalchemy.base import AuditBase, Base
from litestar.contrib.sqlalchemy.init_plugin import SQLAlchemyAsyncConfig, SQLAlchemyInitPlugin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


# the SQLAlchemy base includes a declarative model for you to use in your models.
# The `Base` class includes a `UUID` based primary key (`id`)
class Author(Base):
    name: Mapped[str]
    dob: Mapped[date]
    books: Mapped[list["Book"]] = relationship(back_populates="author", lazy="selectin")


# The `AuditBase` class includes the same UUID` based primary key (`id`) and 2 additional columns: `created` and `updated`.
# `created` is a timestamp of when the record created, and `updated` is the last time the record was modified.
class Book(AuditBase):
    title: Mapped[str]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True, viewonly=True)


@get(path="/sqlalchemy-app")
async def async_sqlalchemy_init(db_session: "AsyncSession", db_engine: "AsyncEngine") -> list[Author]:
    """Interact with SQLAlchemy engine and session."""
    return await db_session.scalars(select(Author))


sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_dependency_key="db_session"
)  # Create 'async_session' dependency.
sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


async def on_startup() -> None:
    """Initializes the database."""
    async with sqlalchemy_config.create_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app = Litestar(
    route_handlers=[async_sqlalchemy_init],
    on_startup=[on_startup],
    plugins=[SQLAlchemyInitPlugin(config=sqlalchemy_config)],
)
