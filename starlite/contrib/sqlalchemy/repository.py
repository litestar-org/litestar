"""SQLAlchemy-based implementation of the repository protocol."""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from starlite.contrib.repository.abc import AbstractRepository
from starlite.contrib.repository.exceptions import ConflictError, RepositoryError
from starlite.contrib.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    LimitOffset,
)

if TYPE_CHECKING:
    from collections import abc
    from datetime import datetime

    from sqlalchemy import Select
    from sqlalchemy.engine import Result
    from sqlalchemy.ext.asyncio import AsyncSession

    from starlite.contrib.repository.types import FilterTypes
    from starlite.contrib.sqlalchemy import base

__all__ = (
    "SQLAlchemyRepository",
    "ModelT",
)

T = TypeVar("T")
ModelT = TypeVar("ModelT", bound="base.Base | base.AuditBase")
SQLARepoT = TypeVar("SQLARepoT", bound="SQLAlchemyRepository")


@contextmanager
def wrap_sqlalchemy_exception() -> Any:
    """Do something within context to raise a `RepositoryError` chained
    from an original `SQLAlchemyError`.

        >>> try:
        ...     with wrap_sqlalchemy_exception():
        ...         raise SQLAlchemyError("Original Exception")
        ... except RepositoryError as exc:
        ...     print(f"caught repository exception from {type(exc.__context__)}")
        ...
        caught repository exception from <class 'sqlalchemy.exc.SQLAlchemyError'>
    """
    try:
        yield
    except IntegrityError as exc:
        raise ConflictError from exc
    except SQLAlchemyError as exc:
        raise RepositoryError(f"An exception occurred: {exc}") from exc


class SQLAlchemyRepository(AbstractRepository[ModelT], Generic[ModelT]):
    """SQLAlchemy based implementation of the repository interface."""

    def __init__(self, *, session: AsyncSession, select_: Select[tuple[ModelT]] | None = None, **kwargs: Any) -> None:
        """Repository pattern for SQLAlchemy models.

        Args:
            session: Session managing the unit-of-work for the operation.
            select_: To facilitate customization of the underlying select query.
        """
        super().__init__(**kwargs)
        self.session = session
        self._select = select(self.model_type) if select_ is None else select_

    async def add(self, data: ModelT) -> ModelT:
        """Add `data` to the collection.

        Args:
            data: Instance to be added to the collection.

        Returns:
            The added instance.
        """
        with wrap_sqlalchemy_exception():
            instance = await self._attach_to_session(data)
            await self.session.flush()
            await self.session.refresh(instance)
            self.session.expunge(instance)
            return instance

    async def delete(self, id_: Any) -> ModelT:
        """Delete instance identified by `id_`.

        Args:
            id_: Identifier of instance to be deleted.

        Returns:
            The deleted instance.

        Raises:
            RepositoryNotFoundException: If no instance found identified by `id_`.
        """
        with wrap_sqlalchemy_exception():
            instance = await self.get(id_)
            await self.session.delete(instance)
            await self.session.flush()
            self.session.expunge(instance)
            return instance

    async def get(self, id_: Any) -> ModelT:
        """Get instance identified by `id_`.

        Args:
            id_: Identifier of the instance to be retrieved.

        Returns:
            The retrieved instance.

        Raises:
            RepositoryNotFoundException: If no instance found identified by `id_`.
        """
        with wrap_sqlalchemy_exception():
            self._filter_select_by_kwargs(**{self.id_attribute: id_})
            instance = (await self._execute()).scalar_one_or_none()
            instance = self.check_not_found(instance)
            self.session.expunge(instance)
            return instance

    async def list(self, *filters: FilterTypes, **kwargs: Any) -> list[ModelT]:
        """Get a list of instances, optionally filtered.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances, after filtering applied.
        """
        for filter_ in filters:
            if isinstance(filter_, LimitOffset):
                self._apply_limit_offset_pagination(filter_.limit, filter_.offset)
            elif isinstance(filter_, BeforeAfter):
                self._filter_on_datetime_field(filter_.field_name, filter_.before, filter_.after)
            elif isinstance(filter_, CollectionFilter):
                self._filter_in_collection(filter_.field_name, filter_.values)
            else:
                raise RepositoryError(f"Unexpected filter: {filter_}")
        self._filter_select_by_kwargs(**kwargs)

        with wrap_sqlalchemy_exception():
            result = await self._execute()
            instances = list(result.scalars())
            for instance in instances:
                self.session.expunge(instance)
            return instances

    async def update(self, data: ModelT) -> ModelT:
        """Update instance with the attribute values present on `data`.

        Args:
            data: An instance that should have a value for `self.id_attribute` that exists in the
                collection.

        Returns:
            The updated instance.

        Raises:
            RepositoryNotFoundException: If no instance found with same identifier as `data`.
        """
        with wrap_sqlalchemy_exception():
            id_ = self.get_id_attribute_value(data)
            # this will raise for not found, and will put the item in the session
            await self.get(id_)
            # this will merge the inbound data to the instance we just put in the session
            instance = await self._attach_to_session(data, strategy="merge")
            await self.session.flush()
            await self.session.refresh(instance)
            self.session.expunge(instance)
            return instance

    async def upsert(self, data: ModelT) -> ModelT:
        """Update or create instance.

        Updates instance with the attribute values present on `data`, or creates a new instance if
        one doesn't exist.

        Args:
            data: Instance to update existing, or be created. Identifier used to determine if an
                existing instance exists is the value of an attribute on `data` named as value of
                `self.id_attribute`.

        Returns:
            The updated or created instance.

        Raises:
            RepositoryNotFoundException: If no instance found with same identifier as `data`.
        """
        with wrap_sqlalchemy_exception():
            instance = await self._attach_to_session(data, strategy="merge")
            await self.session.flush()
            await self.session.refresh(instance)
            self.session.expunge(instance)
            return instance

    def filter_collection_by_kwargs(self, **kwargs: Any) -> None:
        """Filter the collection by kwargs.

        Args:
            **kwargs: key/value pairs such that objects remaining in the collection after filtering
                have the property that their attribute named `key` has value equal to `value`.
        """
        with wrap_sqlalchemy_exception():
            self._select.filter_by(**kwargs)

    @classmethod
    async def check_health(cls, session: AsyncSession) -> bool:
        """Perform a health check on the database.

        Args:
            session: through which we runa check statement

        Returns:
            `True` if healthy.
        """
        return (  # type:ignore[no-any-return]  # pragma: no cover
            await session.execute(text("SELECT 1"))
        ).scalar_one() == 1

    # the following is all sqlalchemy implementation detail, and shouldn't be directly accessed

    def _apply_limit_offset_pagination(self, limit: int, offset: int) -> None:
        self._select = self._select.limit(limit).offset(offset)

    async def _attach_to_session(self, model: ModelT, strategy: Literal["add", "merge"] = "add") -> ModelT:
        """Attach detached instance to the session.

        Args:
            model: The instance to be attached to the session.
            strategy: How the instance should be attached.
                - "add": New instance added to session
                - "merge": Instance merged with existing, or new one added.

        Returns:
            Instance attached to the session - if `"merge"` strategy, may not be same instance
            that was provided.
        """
        if strategy == "add":
            self.session.add(model)
            return model
        if strategy == "merge":
            return await self.session.merge(model)
        raise ValueError("Unexpected value for `strategy`, must be `'add'` or `'merge'`")

    async def _execute(self) -> Result[tuple[ModelT, ...]]:
        return await self.session.execute(self._select)

    def _filter_in_collection(self, field_name: str, values: abc.Collection[Any]) -> None:
        if not values:
            return
        self._select = self._select.where(getattr(self.model_type, field_name).in_(values))

    def _filter_on_datetime_field(self, field_name: str, before: datetime | None, after: datetime | None) -> None:
        field = getattr(self.model_type, field_name)
        if before is not None:
            self._select = self._select.where(field < before)
        if after is not None:
            self._select = self._select.where(field > before)

    def _filter_select_by_kwargs(self, **kwargs: Any) -> None:
        for key, val in kwargs.items():
            self._select = self._select.where(getattr(self.model_type, key) == val)
