"""Example domain objects for testing."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from advanced_alchemy import base
from advanced_alchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemySyncRepository
from sqlalchemy import Column, FetchedValue, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class UUIDAuthor(base.UUIDAuditBase):
    """The UUIDAuthor domain object."""

    name: Mapped[str] = mapped_column(String(length=100))
    dob: Mapped[date] = mapped_column(nullable=True)
    books: Mapped[list[UUIDBook]] = relationship(
        lazy="selectin",
        back_populates="author",
        cascade="all, delete",
    )


class UUIDBook(base.UUIDBase):
    """The Book domain object."""

    title: Mapped[str] = mapped_column(String(length=250))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("uuid_author.id"))
    author: Mapped[UUIDAuthor] = relationship(lazy="joined", innerjoin=True, back_populates="books")


class UUIDEventLog(base.UUIDAuditBase):
    """The event log domain object."""

    logged_at: Mapped[datetime] = mapped_column(default=datetime.now())
    payload: Mapped[dict] = mapped_column(default={})


class UUIDModelWithFetchedValue(base.UUIDBase):
    """The ModelWithFetchedValue UUIDBase."""

    val: Mapped[int]
    updated: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        server_onupdate=FetchedValue(),
    )


uuid_item_tag = Table(
    "uuid_item_tag",
    base.orm_registry.metadata,
    Column("item_id", ForeignKey("uuid_item.id"), primary_key=True),
    Column("tag_id", ForeignKey("uuid_tag.id"), primary_key=True),
)


class UUIDItem(base.UUIDBase):
    name: Mapped[str] = mapped_column(String(length=50))
    description: Mapped[str] = mapped_column(String(length=100), nullable=True)
    tags: Mapped[list[UUIDTag]] = relationship(secondary=lambda: uuid_item_tag, back_populates="items")


class UUIDTag(base.UUIDAuditBase):
    """The event log domain object."""

    name: Mapped[str] = mapped_column(String(length=50))
    items: Mapped[list[UUIDItem]] = relationship(secondary=lambda: uuid_item_tag, back_populates="tags")


class UUIDRule(base.UUIDAuditBase):
    """The rule domain object."""

    name: Mapped[str] = mapped_column(String(length=250))
    config: Mapped[dict] = mapped_column(default=lambda: {})


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


class TagAsyncRepository(SQLAlchemyAsyncRepository[UUIDTag]):
    """Tag repository."""

    model_type = UUIDTag


class ItemAsyncRepository(SQLAlchemyAsyncRepository[UUIDItem]):
    """Item repository."""

    model_type = UUIDItem


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


class TagSyncRepository(SQLAlchemySyncRepository[UUIDTag]):
    """Tag repository."""

    model_type = UUIDTag


class ItemSyncRepository(SQLAlchemySyncRepository[UUIDItem]):
    """Item repository."""

    model_type = UUIDItem
