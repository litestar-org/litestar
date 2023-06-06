"""Example domain objects for testing."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from litestar.contrib.sqlalchemy.base import BigIntAuditBase, BigIntBase
from litestar.contrib.sqlalchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemySyncRepository


class BigIntAuthor(BigIntAuditBase):
    """The Author domain object."""

    name: Mapped[str] = mapped_column(String(length=100))  # pyright: ignore
    dob: Mapped[date] = mapped_column(nullable=True)  # pyright: ignore


class BigIntBook(BigIntBase):
    """The Book domain object."""

    title: Mapped[str] = mapped_column(String(length=250))  # pyright: ignore
    author_id: Mapped[int] = mapped_column(ForeignKey("big_int_author.id"))  # pyright: ignore
    author: Mapped[BigIntAuthor] = relationship(lazy="joined", innerjoin=True)  # pyright: ignore


class BigIntEventLog(BigIntAuditBase):
    """The event log domain object."""

    logged_at: Mapped[datetime] = mapped_column(default=datetime.now())  # pyright: ignore
    payload: Mapped[dict] = mapped_column(default=lambda: {})  # pyright: ignore


class BigIntRule(BigIntAuditBase):
    """The rule domain object."""

    name: Mapped[str] = mapped_column(String(length=250))  # pyright: ignore
    config: Mapped[dict] = mapped_column(default={})  # pyright: ignore


class RuleAsyncRepository(SQLAlchemyAsyncRepository[BigIntRule]):
    """Rule repository."""

    model_type = BigIntRule


class AuthorAsyncRepository(SQLAlchemyAsyncRepository[BigIntAuthor]):
    """Author repository."""

    model_type = BigIntAuthor


class BookAsyncRepository(SQLAlchemyAsyncRepository[BigIntBook]):
    """Book repository."""

    model_type = BigIntBook


class EventLogAsyncRepository(SQLAlchemyAsyncRepository[BigIntEventLog]):
    """Event log repository."""

    model_type = BigIntEventLog


class AuthorSyncRepository(SQLAlchemySyncRepository[BigIntAuthor]):
    """Author repository."""

    model_type = BigIntAuthor


class BookSyncRepository(SQLAlchemySyncRepository[BigIntBook]):
    """Book repository."""

    model_type = BigIntBook


class EventLogSyncRepository(SQLAlchemySyncRepository[BigIntEventLog]):
    """Event log repository."""

    model_type = BigIntEventLog


class RuleSyncRepository(SQLAlchemySyncRepository[BigIntRule]):
    """Rule repository."""

    model_type = BigIntRule
