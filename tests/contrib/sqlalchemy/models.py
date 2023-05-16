"""Example domain objects for testing."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar.contrib.sqlalchemy.base import BigIntAuditBase, BigIntBase, UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemySyncRepository


class Author(UUIDAuditBase):
    """The Author domain object."""

    name: Mapped[str] = mapped_column(String(length=100))  # pyright: ignore
    dob: Mapped[date] = mapped_column(nullable=True)  # pyright: ignore


class Book(UUIDBase):
    """The Book domain object."""

    title: Mapped[str] = mapped_column(String(length=250))  # pyright: ignore
    author_id: Mapped[UUID] = mapped_column(ForeignKey("author.id"))  # pyright: ignore
    author: Mapped[Author] = relationship(lazy="joined", innerjoin=True)  # pyright: ignore


class EventLog(UUIDAuditBase):
    """The event log domain object."""

    logged_at: Mapped[datetime] = mapped_column(default=datetime.now())  # pyright: ignore
    payload: Mapped[dict] = mapped_column(default={})  # pyright: ignore


class Store(BigIntAuditBase):
    """The store domain object."""

    store_name: Mapped[str] = mapped_column(String(length=250))  # pyright: ignore


class Ingredient(BigIntBase):
    """The ingredient domain object."""

    name: Mapped[str] = mapped_column(String(length=250))  # pyright: ignore


class AuthorAsyncRepository(SQLAlchemyAsyncRepository[Author]):
    """Author repository."""

    model_type = Author


class BookAsyncRepository(SQLAlchemyAsyncRepository[Book]):
    """Book repository."""

    model_type = Book


class EventLogAsyncRepository(SQLAlchemyAsyncRepository[EventLog]):
    """Event log repository."""

    model_type = EventLog


class StoreAsyncRepository(SQLAlchemyAsyncRepository[Store]):
    """Store repository."""

    model_type = Store


class IngredientAsyncRepository(SQLAlchemyAsyncRepository[Ingredient]):
    """Ingredient repository."""

    model_type = Ingredient


class AuthorSyncRepository(SQLAlchemySyncRepository[Author]):
    """Author repository."""

    model_type = Author


class BookSyncRepository(SQLAlchemySyncRepository[Book]):
    """Book repository."""

    model_type = Book


class EventLogSyncRepository(SQLAlchemySyncRepository[EventLog]):
    """Event log repository."""

    model_type = EventLog


class StoreSyncRepository(SQLAlchemySyncRepository[Store]):
    """Store repository."""

    model_type = Store


class IngredientSyncRepository(SQLAlchemySyncRepository[Ingredient]):
    """Ingredient repository."""

    model_type = Ingredient
