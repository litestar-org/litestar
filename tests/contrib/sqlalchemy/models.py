"""Example domain objects for testing."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository


class Author(UUIDAuditBase):
    """The Author domain object."""

    name: Mapped[str] = mapped_column(String(length=100))
    dob: Mapped[date] = mapped_column(nullable=True)


class Book(UUIDBase):
    """The Book domain object."""

    title: Mapped[str] = mapped_column(String(length=250))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True)


class EventLog(UUIDAuditBase):
    """The event log domain object."""

    logged_at: Mapped[datetime] = mapped_column(default=datetime.now())
    payload: Mapped[dict] = mapped_column(default={})


class AuthorRepository(SQLAlchemyAsyncRepository[Author]):
    """Author repository."""

    model_type = Author


class BookRepository(SQLAlchemyAsyncRepository[Book]):
    """Author repository."""

    model_type = Book


class EventLogRepository(SQLAlchemyAsyncRepository[EventLog]):
    """Event log repository."""

    model_type = EventLog
