from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.plugins import SQLAlchemyAsyncConfig


# the SQLAlchemy base includes a declarative model for you to use in your models.
# The `Base` class includes a `UUID` based primary key (`id`)
class Author(UUIDBase):
    name: Mapped[str]
    dob: Mapped[date]
    books: Mapped[list["Book"]] = relationship(back_populates="author", lazy="selectin")


# The `AuditBase` class includes the same UUID` based primary key (`id`) and 2 additional columns: `created` and `updated`.
# `created` is a timestamp of when the record created, and `updated` is the last time the record was modified.
class Book(UUIDAuditBase):
    title: Mapped[str]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True, viewonly=True)


sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite",
    session_dependency_key="db_session",
)


async def on_startup() -> None:
    """Initializes the database."""
    async with sqlalchemy_config.create_engine().begin() as conn:
        await conn.run_sync(UUIDBase.metadata.create_all)
