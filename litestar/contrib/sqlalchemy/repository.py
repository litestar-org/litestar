"""SQLAlchemy-based implementation of the repository protocol."""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generic, Literal, Tuple, TypeVar, cast

from sqlalchemy import Select, delete, over, select, text, update
from sqlalchemy import func as sql_func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from litestar.contrib.repository.abc import AbstractAsyncRepository
from litestar.contrib.repository.exceptions import ConflictError, RepositoryError
from litestar.contrib.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    LimitOffset,
    OrderBy,
    SearchFilter,
)

if TYPE_CHECKING:
    from collections import abc
    from datetime import datetime

    from sqlalchemy.engine import Result
    from sqlalchemy.ext.asyncio import AsyncSession

    from litestar.contrib.repository import FilterTypes

    from . import base

__all__ = (
    "SQLAlchemyAsyncRepository",
    "ModelT",
)

T = TypeVar("T")
ModelT = TypeVar("ModelT", bound="base.ModelProtocol")
SQLARepoT = TypeVar("SQLARepoT", bound="SQLAlchemyAsyncRepository")
SelectT = TypeVar("SelectT", bound="Select[Any]")
RowT = TypeVar("RowT", bound=Tuple[Any, ...])


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


class SQLAlchemyAsyncRepository(AbstractAsyncRepository[ModelT], Generic[ModelT]):
    """SQLAlchemy based implementation of the repository interface."""

    match_fields: list[str] | str | None = None

    def __init__(self, *, statement: Select[tuple[ModelT]] | None = None, session: AsyncSession, **kwargs: Any) -> None:
        """Repository pattern for SQLAlchemy models.

        Args:
            statement: To facilitate customization of the underlying select query.
            session: Session managing the unit-of-work for the operation.
            **kwargs: Additional arguments.

        """
        super().__init__(**kwargs)
        self.session = session
        self.statement = statement if statement is not None else select(self.model_type)

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

    async def add_many(self, data: list[ModelT]) -> list[ModelT]:
        """Add Many `data` to the collection.

        Args:
            data: list of Instances to be added to the collection.


        Returns:
            The added instances.
        """
        with wrap_sqlalchemy_exception():
            self.session.add_all(data)
            await self.session.flush()
            for datum in data:
                self.session.expunge(datum)
            return data

    async def delete(self, item_id: Any) -> ModelT:
        """Delete instance identified by ``item_id``.

        Args:
            item_id: Identifier of instance to be deleted.

        Returns:
            The deleted instance.

        Raises:
            NotFoundError: If no instance found identified by ``item_id``.
        """
        with wrap_sqlalchemy_exception():
            instance = await self.get(item_id)
            await self.session.delete(instance)
            await self.session.flush()
            self.session.expunge(instance)
            return instance

    async def delete_many(self, item_ids: list[Any]) -> list[ModelT]:
        """Delete instance identified by `item_id`.

        Args:
            item_ids: Identifier of instance to be deleted.

        Returns:
            The deleted instances.

        """
        with wrap_sqlalchemy_exception():
            instances: list[ModelT] = []
            chunk_size = 450
            for idx in range(0, len(item_ids), chunk_size):
                chunk = item_ids[idx : min(idx + chunk_size, len(item_ids))]
                if self.session.bind.dialect.delete_executemany_returning:
                    instances.extend(
                        await self.session.scalars(
                            delete(self.model_type)
                            .where(getattr(self.model_type, self.id_attribute).in_(chunk))
                            .returning(self.model_type)
                        )
                    )
                else:
                    instances.extend(
                        await self.session.scalars(
                            select(self.model_type).where(getattr(self.model_type, self.id_attribute).in_(chunk))
                        )
                    )
                    await self.session.execute(
                        delete(self.model_type).where(getattr(self.model_type, self.id_attribute).in_(chunk))
                    )
            await self.session.flush()
            for instance in instances:
                self.session.expunge(instance)
            return instances

    async def exists(self, **kwargs: Any) -> bool:
        """Return true if the object specified by ``kwargs`` exists.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            True if the instance was found.  False if not found..

        """
        existing = await self.count(**kwargs)
        return bool(existing > 0)

    async def get(self, item_id: Any, **kwargs: Any) -> ModelT:
        """Get instance identified by `item_id`.

        Args:
            item_id: Identifier of the instance to be retrieved.
            **kwargs: Additional parameters

        Returns:
            The retrieved instance.

        Raises:
            NotFoundError: If no instance found identified by `item_id`.
        """
        with wrap_sqlalchemy_exception():
            statement = kwargs.pop("statement", self.statement)
            statement = self._filter_select_by_kwargs(statement=statement, **{self.id_attribute: item_id})
            instance = (await self._execute(statement)).scalar_one_or_none()
            instance = self.check_not_found(instance)
            self.session.expunge(instance)
            return instance

    async def get_one(self, **kwargs: Any) -> ModelT:
        """Get instance identified by ``kwargs``.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            The retrieved instance.

        Raises:
            NotFoundError: If no instance found identified by `item_id`.
        """
        with wrap_sqlalchemy_exception():
            statement = kwargs.pop("statement", self.statement)
            statement = self._filter_select_by_kwargs(statement=statement, **kwargs)
            instance = (await self._execute(statement)).scalar_one_or_none()
            instance = self.check_not_found(instance)
            self.session.expunge(instance)
            return instance

    async def get_one_or_none(self, **kwargs: Any) -> ModelT | None:
        """Get instance identified by ``kwargs`` or None if not found.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            The retrieved instance or None
        """
        with wrap_sqlalchemy_exception():
            statement = kwargs.pop("statement", self.statement)
            statement = self._filter_select_by_kwargs(statement=statement, **kwargs)
            instance = (await self._execute(statement)).scalar_one_or_none()
            if instance:
                self.session.expunge(instance)
            return instance  # type: ignore

    async def get_or_create(
        self, match_fields: list[str] | str | None = None, upsert: bool = True, **kwargs: Any
    ) -> tuple[ModelT, bool]:
        """Get instance identified by ``kwargs`` or create if it doesn't exist.

        Args:
            match_fields: a list of keys to use to match the existing model.  When empty, all fields are matched.
            upsert: When using match_fields and actual model values differ from `kwargs`, perform an update operation on the model.
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            a tuple that includes the instance and whether or not it needed to be created.  When using match_fields and actual model values differ from `kwargs`, the model value will be updated.
        """
        match_fields = match_fields if match_fields else self.match_fields
        if isinstance(match_fields, str):
            match_fields = [match_fields]
        if match_fields:
            match_filter = {
                field_name: kwargs.get(field_name, None)
                for field_name in match_fields
                if kwargs.get(field_name, None) is not None
            }
        else:
            match_filter = kwargs
        existing = await self.get_one_or_none(**match_filter)
        if not existing:
            return await self.add(self.model_type(**kwargs)), True
        if upsert:
            for field_name, new_field_value in kwargs.items():
                field = getattr(existing, field_name, None)
                if field and field != new_field_value:
                    setattr(existing, field_name, new_field_value)
            if existing in self.session.dirty:
                return (await self.update(existing)), False
        return existing, False

    async def count(self, *filters: FilterTypes, **kwargs: Any) -> int:
        """Get the count of records returned by a query.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            Count of records returned by query, ignoring pagination.
        """
        statement = kwargs.pop("statement", self.statement)
        statement = statement.with_only_columns(
            sql_func.count(self.get_id_attribute_value(self.model_type)),
            maintain_column_froms=True,
        ).order_by(None)
        statement = self._apply_filters(*filters, apply_pagination=False, statement=statement)
        statement = self._filter_select_by_kwargs(statement, **kwargs)
        results = await self._execute(statement)
        return results.scalar_one()  # type: ignore

    async def update(self, data: ModelT) -> ModelT:
        """Update instance with the attribute values present on `data`.

        Args:
            data: An instance that should have a value for `self.id_attribute` that exists in the
                collection.

        Returns:
            The updated instance.

        Raises:
            NotFoundError: If no instance found with same identifier as `data`.
        """
        with wrap_sqlalchemy_exception():
            item_id = self.get_id_attribute_value(data)
            # this will raise for not found, and will put the item in the session
            await self.get(item_id)
            # this will merge the inbound data to the instance we just put in the session
            instance = await self._attach_to_session(data, strategy="merge")
            await self.session.flush()
            await self.session.refresh(instance)
            self.session.expunge(instance)
            return instance

    async def update_many(self, data: list[ModelT]) -> list[ModelT]:
        """Update one or more instances with the attribute values present on `data`.

        This function has an optimized bulk insert based on the configured SQL dialect:
        - For backends supporting `RETURNING` with `executemany`, a single bulk insert with returning clause is executed.
        - For other backends, it does a bulk insert and then selects the inserted records

        Args:
            data: A list of instances to update.  Each should have a value for `self.id_attribute` that exists in the
                collection.

        Returns:
            The updated instances.

        Raises:
            NotFoundError: If no instance found with same identifier as `data`.
        """
        data_to_update: list[dict[str, Any]] = [v.to_dict() if isinstance(v, self.model_type) else v for v in data]  # type: ignore
        with wrap_sqlalchemy_exception():
            if self.session.bind.dialect.update_executemany_returning:
                instances = list(
                    await self.session.scalars(  # type: ignore
                        update(self.model_type).returning(self.model_type),
                        data_to_update,  # pyright: ignore[reportGeneralTypeIssues]
                    )
                )
                await self.session.flush()
                for instance in instances:
                    self.session.expunge(instance)
                return instances
            await self.session.execute(
                update(self.model_type),
                data_to_update,
            )
            await self.session.flush()
            return data

    async def list_and_count(
        self,
        *filters: FilterTypes,
        **kwargs: Any,
    ) -> tuple[list[ModelT], int]:
        """List records with total count.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            Count of records returned by query, ignoring pagination.
        """
        statement = kwargs.pop("statement", self.statement)
        statement = statement.add_columns(over(sql_func.count(self.get_id_attribute_value(self.model_type))))
        statement = self._apply_filters(*filters, statement=statement)
        statement = self._filter_select_by_kwargs(statement, **kwargs)
        with wrap_sqlalchemy_exception():
            result = await self._execute(statement)
            count: int = 0
            instances: list[ModelT] = []
            for i, (instance, count_value) in enumerate(result):
                self.session.expunge(instance)
                instances.append(instance)
                if i == 0:
                    count = count_value
            return instances, count

    async def list(self, *filters: FilterTypes, **kwargs: Any) -> list[ModelT]:
        """Get a list of instances, optionally filtered.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances, after filtering applied.
        """
        statement = kwargs.pop("statement", self.statement)
        statement = self._apply_filters(*filters, statement=statement)
        statement = self._filter_select_by_kwargs(statement, **kwargs)

        with wrap_sqlalchemy_exception():
            result = await self._execute(statement)
            instances = list(result.scalars())
            for instance in instances:
                self.session.expunge(instance)
            return instances

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
            NotFoundError: If no instance found with same identifier as `data`.
        """
        with wrap_sqlalchemy_exception():
            instance = await self._attach_to_session(data, strategy="merge")
            await self.session.flush()
            await self.session.refresh(instance)
            self.session.expunge(instance)
            return instance

    def filter_collection_by_kwargs(  # type:ignore[override]
        self, collection: SelectT, /, **kwargs: Any
    ) -> SelectT:
        """Filter the collection by kwargs.

        Args:
            collection: statement to filter
            **kwargs: key/value pairs such that objects remaining in the collection after filtering
                have the property that their attribute named `key` has value equal to `value`.
        """
        with wrap_sqlalchemy_exception():
            return collection.filter_by(**kwargs)

    @classmethod
    async def check_health(cls, session: AsyncSession) -> bool:
        """Perform a health check on the database.

        Args:
            session: through which we run a check statement

        Returns:
            `True` if healthy.
        """
        return (  # type:ignore[no-any-return]  # pragma: no cover
            await session.execute(text("SELECT 1"))
        ).scalar_one() == 1

    # the following is all sqlalchemy implementation detail, and shouldn't be directly accessed

    def _apply_limit_offset_pagination(self, limit: int, offset: int, statement: SelectT) -> SelectT:
        return statement.limit(limit).offset(offset)

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

    async def _execute(self, statement: Select[RowT]) -> Result[RowT]:
        return cast("Result[RowT]", await self.session.execute(statement))

    def _apply_filters(self, *filters: FilterTypes, apply_pagination: bool = True, statement: SelectT) -> SelectT:
        """Apply filters to a select statement.

        Args:
            *filters: filter types to apply to the query
            apply_pagination: applies pagination filters if true
            statement: select statement to apply filters

        Keyword Args:
            select: select to apply filters against

        Returns:
            The select with filters applied.
        """
        for filter_ in filters:
            if isinstance(filter_, LimitOffset):
                if apply_pagination:
                    statement = self._apply_limit_offset_pagination(filter_.limit, filter_.offset, statement=statement)
            elif isinstance(filter_, BeforeAfter):
                statement = self._filter_on_datetime_field(
                    filter_.field_name, filter_.before, filter_.after, statement=statement
                )
            elif isinstance(filter_, CollectionFilter):
                statement = self._filter_in_collection(filter_.field_name, filter_.values, statement=statement)
            elif isinstance(filter_, OrderBy):
                statement = self._order_by(statement, filter_.field_name, sort_desc=bool(filter_.sort_order == "desc"))
            elif isinstance(filter_, SearchFilter):
                statement = self._filter_by_like(
                    statement, filter_.field_name, value=filter_.value, ignore_case=bool(filter_.ignore_case)
                )
            else:
                raise RepositoryError(f"Unexpected filter: {filter_}")
        return statement

    def _filter_in_collection(self, field_name: str, values: abc.Collection[Any], statement: SelectT) -> SelectT:
        if not values:
            return statement
        return statement.where(getattr(self.model_type, field_name).in_(values))

    def _filter_on_datetime_field(
        self, field_name: str, before: datetime | None, after: datetime | None, statement: SelectT
    ) -> SelectT:
        field = getattr(self.model_type, field_name)
        if before is not None:
            statement = statement.where(field < before)
        if after is not None:
            statement = statement.where(field > before)
        return statement

    def _filter_select_by_kwargs(self, statement: SelectT, **kwargs: Any) -> SelectT:
        for key, val in kwargs.items():
            statement = statement.where(getattr(self.model_type, key) == val)
        return statement

    def _filter_by_like(self, statement: SelectT, field_name: str, value: str, ignore_case: bool) -> SelectT:
        field = getattr(self.model_type, field_name)
        search_text = f"%{value}%"
        return statement.where(field.ilike(search_text) if ignore_case else field.like(search_text))

    def _order_by(self, statement: SelectT, field_name: str, sort_desc: bool = False) -> SelectT:
        field = getattr(self.model_type, field_name)
        return statement.order_by(field.desc() if sort_desc else field.asc())
