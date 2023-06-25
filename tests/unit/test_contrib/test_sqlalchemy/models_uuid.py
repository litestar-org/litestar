"""Example domain objects for testing."""

from __future__ import annotations

from datetime import date, datetime
from typing import List
from uuid import UUID

from sqlalchemy import FetchedValue, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar.contrib.sqlalchemy.base import UUIDAuditBase, UUIDBase
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemySyncRepository


class UUIDAuthor(UUIDAuditBase):
    """The UUIDAuthor domain object."""

    name: Mapped[str] = mapped_column(String(length=100))  # pyright: ignore
    dob: Mapped[date] = mapped_column(nullable=True)  # pyright: ignore
    books: Mapped[List[UUIDBook]] = relationship(  # pyright: ignore  # noqa: UP
        lazy="selectin",
        back_populates="author",
        cascade="all, delete",
    )


class UUIDBook(UUIDBase):
    """The Book domain object."""

    title: Mapped[str] = mapped_column(String(length=250))  # pyright: ignore
    author_id: Mapped[UUID] = mapped_column(ForeignKey("uuid_author.id"))  # pyright: ignore
    author: Mapped[UUIDAuthor] = relationship(lazy="joined", innerjoin=True, back_populates="books")  # pyright: ignore


class UUIDEventLog(UUIDAuditBase):
    """The event log domain object."""

    logged_at: Mapped[datetime] = mapped_column(default=datetime.now())  # pyright: ignore
    payload: Mapped[dict] = mapped_column(default={})  # pyright: ignore


class UUIDModelWithFetchedValue(UUIDBase):
    """The ModelWithFetchedValue UUIDBase."""

    val: Mapped[int]
    updated: Mapped[str] = mapped_column(
        String(length=250), server_default=func.random(), onupdate=func.random(), server_onupdate=FetchedValue()
    )


class UUIDRule(UUIDAuditBase):
    """The rule domain object."""

    name: Mapped[str] = mapped_column(String(length=250))  # pyright: ignore
    config: Mapped[dict] = mapped_column(default=lambda: {})  # pyright: ignore


class RuleAsyncRepository(SQLAlchemyAsyncRepository[UUIDRule]):
    """Rule repository."""

    model_type = UUIDRule


class AuthorAsyncRepository(SQLAlchemyAsyncRepository[UUIDAuthor]):
    """Author repository."""

    model_type = UUIDAuthor


class BookAsyncRepository(SQLAlchemyAsyncRepository[UUIDBook]):
    """Book repository."""

    model_type = UUIDBook


class EventLogAsyncRepository(SQLAlchemyAsyncRepository[UUIDEventLog]):
    """Event log repository."""

    model_type = UUIDEventLog


class ModelWithFetchedValueAsyncRepository(SQLAlchemyAsyncRepository[UUIDModelWithFetchedValue]):
    """ModelWithFetchedValue repository."""

    model_type = UUIDModelWithFetchedValue


class AuthorSyncRepository(SQLAlchemySyncRepository[UUIDAuthor]):
    """Author repository."""

    model_type = UUIDAuthor


class BookSyncRepository(SQLAlchemySyncRepository[UUIDBook]):
    """Book repository."""

    model_type = UUIDBook


class EventLogSyncRepository(SQLAlchemySyncRepository[UUIDEventLog]):
    """Event log repository."""

    model_type = UUIDEventLog


class RuleSyncRepository(SQLAlchemySyncRepository[UUIDRule]):
    """Rule repository."""

    model_type = UUIDRule


class ModelWithFetchedValueSyncRepository(SQLAlchemySyncRepository[UUIDModelWithFetchedValue]):
    """ModelWithFetchedValue repository."""

    model_type = UUIDModelWithFetchedValue
