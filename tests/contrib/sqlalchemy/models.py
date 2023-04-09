"""Example domain objects for testing."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar.contrib.sqlalchemy.base import AuditBase, Base
from litestar.contrib.sqlalchemy.repository import AsyncSQLAlchemyRepository


class Author(AuditBase):
    """The Author domain object."""

    name: Mapped[str]
    dob: Mapped[date] = mapped_column(nullable=True)


class Book(Base):
    """The Book domain object."""

    title: Mapped[str]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True)


class AuthorRepository(AsyncSQLAlchemyRepository[Author]):
    """Author repository."""

    model_type = Author


class BookRepository(AsyncSQLAlchemyRepository[Book]):
    """Author repository."""

    model_type = Book
