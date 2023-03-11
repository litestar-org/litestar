"""A repository implementation for tests.

Uses a `dict` for storage.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import uuid4

from starlite.contrib.repository.abc import AbstractRepository
from starlite.contrib.repository.exceptions import ConflictError, RepositoryError

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, MutableMapping
    from typing import Any

    from starlite.contrib.repository.types import FilterTypes
    from starlite.contrib.sqlalchemy import base

ModelT = TypeVar("ModelT", bound="base.Base | base.AuditBase")
MockRepoT = TypeVar("MockRepoT", bound="GenericMockRepository")


class GenericMockRepository(AbstractRepository[ModelT], Generic[ModelT]):
    """A repository implementation for tests.

    Uses a :class:`dict` for storage.
    """

    collection: MutableMapping[Hashable, ModelT]
    model_type: type[ModelT]

    def __init__(self, id_factory: Callable[[], Any] = uuid4, **_: Any) -> None:
        super().__init__()
        self._id_factory = id_factory

    @classmethod
    def __class_getitem__(cls: type[MockRepoT], item: type[ModelT]) -> type[MockRepoT]:
        """Add collection to ``_collections`` for the type.

        Args:
            item: The type that the class has been parametrized with.
        """
        return type(  # pyright:ignore
            f"{cls.__name__}[{item.__name__}]", (cls,), {"collection": {}, "model_type": item}
        )

    def _find_or_raise_not_found(self, item_id: Any) -> ModelT:
        return self.check_not_found(self.collection.get(item_id))

    async def add(self, data: ModelT, allow_id: bool = False) -> ModelT:
        """Add ``data`` to the collection.

        Args:
            data: Instance to be added to the collection.
            allow_id: disable the identified object check.

        Returns:
            The added instance.
        """
        if allow_id is False and self.get_id_attribute_value(data) is not None:
            raise ConflictError("`add()` received identified item.")
        now = datetime.now()  # noqa: DTZ005
        if hasattr(data, "updated") and hasattr(data, "created"):
            # maybe the @declarative_mixin decorator doesn't play nice with pyright?
            data.updated = data.created = now  # pyright: ignore
        if allow_id is False:
            id_ = self._id_factory()
            self.set_id_attribute_value(id_, data)
        self.collection[data.id] = data
        return data

    async def add_many(self, data: list[ModelT], allow_id: bool = False) -> list[ModelT]:
        """Add multiple ``data`` to the collection.

        Args:
            data: Instance to be added to the collection.
            allow_id: disable the identified object check.

        Returns:
            The added instance.
        """
        now = datetime.now()  # noqa: DTZ005
        for data_row in data:
            if allow_id is False and self.get_id_attribute_value(data_row) is not None:
                raise ConflictError("`add()` received identified item.")

            if hasattr(data, "updated") and hasattr(data, "created"):
                # maybe the @declarative_mixin decorator doesn't play nice with pyright?
                data.updated = data.created = now  # pyright: ignore
            if allow_id is False:
                id_ = self._id_factory()
                self.set_id_attribute_value(id_, data_row)
                self.collection[data_row.id] = data_row
        return data

    async def delete(self, item_id: Any) -> ModelT:
        """Delete instance identified by ``item_id``.

        Args:
            item_id: Identifier of instance to be deleted.

        Returns:
            The deleted instance.

        Raises:
            RepositoryNotFoundException: If no instance found identified by ``item_id``.
        """
        try:
            return self._find_or_raise_not_found(item_id)
        finally:
            del self.collection[item_id]

    async def delete_many(self, item_ids: list[Any]) -> list[ModelT]:
        """Delete instances identified by list of identifiers ``item_ids``.

        Args:
            item_ids: list of identifiers of instances to be deleted.

        Returns:
            The deleted instances.

        """
        instances: list[ModelT] = []
        for item_id in item_ids:
            obj = await self.get_one_or_none(**{self.id_attribute: item_id})
            if obj:
                obj = await self.delete(obj.id)
                instances.append(obj)
        return instances

    async def exists(self, **kwargs: Any) -> bool:
        """Return true if the object specified by ``kwargs`` exists.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            True if the instance was found.  False if not found..

        """
        existing = await self.get_one_or_none(**kwargs)
        return bool(existing)

    async def get(self, item_id: Any, **kwargs: Any) -> ModelT:
        """Get instance identified by ``item_id``.

        Args:
            item_id: Identifier of the instance to be retrieved.
            **kwargs: additional arguments

        Returns:
            The retrieved instance.

        Raises:
            RepositoryNotFoundException: If no instance found identified by ``item_id``.
        """
        return self._find_or_raise_not_found(item_id)

    async def get_or_create(self, **kwargs: Any) -> tuple[ModelT, bool]:
        """Get instance identified by ``kwargs`` or create if it doesn't exist.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            a tuple that includes the instance and whether or not it needed to be created.

        """
        existing = await self.get_one_or_none(**kwargs)
        if existing:
            return (existing, False)
        return (await self.add(self.model_type(**kwargs)), True)  # type: ignore[arg-type]

    async def get_one(self, **kwargs: Any) -> ModelT:
        """Get instance identified by query filters.

        Args:
            **kwargs: Instance attribute value filters.

        Returns:
            The retrieved instance or None

        Raises:
            RepositoryNotFoundException: If no instance found identified by ``kwargs``.
        """
        data = await self.list(**kwargs)
        return self.check_not_found(data[0] if len(data) > 0 else None)

    async def get_one_or_none(self, **kwargs: Any) -> ModelT | None:
        """Get instance identified by query filters or None if not found.

        Args:
            **kwargs: Instance attribute value filters.

        Returns:
            The retrieved instance or None
        """
        data = await self.list(**kwargs)
        return data[0] if len(data) > 0 else None

    async def count(self, *filters: FilterTypes, **kwargs: Any) -> int:
        """Count of rows returned by query.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            Count of instances in collection, ignoring pagination.
        """
        return len(await self.list(*filters, **kwargs))

    async def update(self, data: ModelT) -> ModelT:
        """Update instance with the attribute values present on ``data``.

        Args:
            data: An instance that should have a value for :attr:`id_attribute <GenericMockRepository.id_attribute>` that exists in the
                collection.

        Returns:
            The updated instance.

        Raises:
            RepositoryNotFoundException: If no instance found with same identifier as ``data``.
        """
        item = self._find_or_raise_not_found(self.get_id_attribute_value(data))
        # should never be modifiable
        if hasattr(data, "updated"):
            # maybe the @declarative_mixin decorator doesn't play nice with pyright?
            data.updated = datetime.now()  # pyright: ignore  # noqa: DTZ005
        for key, val in data.__dict__.items():
            if key.startswith("_"):
                continue
            setattr(item, key, val)
        return item

    async def update_many(self, data: list[ModelT]) -> list[ModelT]:
        """Update instances with the attribute values present on ``data``.

        Args:
            data: A list of instances that should have a value for :attr:`id_attribute <GenericMockRepository.id_attribute>` that exists in the
                collection.

        Returns:
            The updated instances.

        Raises:
            RepositoryNotFoundException: If no instance found with same identifier as ``data``.
        """
        items = [self._find_or_raise_not_found(self.get_id_attribute_value(row)) for row in data]
        # should never be modifiable
        for item in items:
            if hasattr(item, "updated"):
                # maybe the @declarative_mixin decorator doesn't play nice with pyright?
                item.updated = datetime.now()  # pyright: ignore # noqa: DTZ005
            for key, val in item.__dict__.items():
                if key.startswith("_"):
                    continue
                setattr(item, key, val)
        return items

    async def upsert(self, data: ModelT) -> ModelT:
        """Update or create instance.

        Updates instance with the attribute values present on ``data``, or creates a new instance if
        one doesn't exist.

        Args:
            data: Instance to update existing, or be created. Identifier used to determine if an
                existing instance exists is the value of an attribute on `data` named as value of
                :attr:`id_attribute <GenericMockRepository.id_attribute>`.

        Returns:
            The updated or created instance.

        Raises:
            RepositoryNotFoundException: If no instance found with same identifier as ``data``.
        """
        item_id = self.get_id_attribute_value(data)
        if item_id in self.collection:
            return await self.update(data)
        return await self.add(data, allow_id=True)

    async def list_and_count(
        self,
        *filters: FilterTypes,
        **kwargs: Any,
    ) -> tuple[list[ModelT], int]:
        """Get a list of instances, optionally filtered with a total row count.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            Count of records returned by query, ignoring pagination.
        """
        return await self.list(*filters, **kwargs), await self.count(*filters, **kwargs)

    async def list(self, *filters: "FilterTypes", **kwargs: Any) -> list[ModelT]:
        """Get a list of instances, optionally filtered.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances, after filtering applied.
        """
        return list(self.filter_collection_by_kwargs(self.collection, **kwargs).values())

    def filter_collection_by_kwargs(  # type:ignore[override]
        self, collection: MutableMapping[Hashable, ModelT], /, **kwargs: Any
    ) -> MutableMapping[Hashable, ModelT]:
        """Filter the collection by kwargs.

        Args:
            collection: set of objects to filter
            **kwargs: key/value pairs such that objects remaining in the collection after filtering
                have the property that their attribute named ``key`` has value equal to ``value``.
        """
        new_collection: dict[Hashable, ModelT] = {}
        for item in self.collection.values():
            try:
                if all(getattr(item, name) == value for name, value in kwargs.items()):
                    new_collection[item.id] = item
            except AttributeError as orig:
                raise RepositoryError from orig
        return new_collection

    @classmethod
    def seed_collection(cls, instances: Iterable[ModelT]) -> None:
        """Seed the collection for repository type.

        Args:
            instances: the instances to be added to the collection.
        """
        for instance in instances:
            cls.collection[cls.get_id_attribute_value(instance)] = instance

    @classmethod
    def clear_collection(cls) -> None:
        """Empty the collection for repository type."""
        cls.collection = {}
