"""Data persistence interface."""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .exceptions import NotFoundError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .types import FilterTypes


__all__ = ("AbstractRepository",)

T = TypeVar("T")
RepoT = TypeVar("RepoT", bound="AbstractRepository")
CollectionT = TypeVar("CollectionT")


class AbstractRepository(Generic[T], metaclass=ABCMeta):
    """Interface for persistent data interaction."""

    model_type: type[T]
    """Type of object represented by the repository."""
    id_attribute = "id"
    """Name of the primary identifying attribute on :attr:`model_type`."""

    def __init__(self, **kwargs: Any) -> None:
        """Repository constructors accept arbitrary kwargs."""
        super().__init__(**kwargs)

    @abstractmethod
    async def add(self, data: T) -> T:
        """Add ``data`` to the collection.

        Args:
            data: Instance to be added to the collection.

        Returns:
            The added instance.
        """

    @abstractmethod
    async def add_many(self, data: Sequence[T]) -> Sequence[T]:
        """Add multiple ``data`` to the collection.

        Args:
            data: Instances to be added to the collection.

        Returns:
            The added instances.
        """

    @abstractmethod
    async def count(self, *filters: FilterTypes, **kwargs: Any) -> int:
        """Get the count of records returned by a query.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            The count of instances
        """

    @abstractmethod
    async def delete(self, item_id: Any) -> T:
        """Delete instance identified by ``item_id``.

        Args:
            item_id: Identifier of instance to be deleted.

        Returns:
            The deleted instance.

        Raises:
            RepositoryNotFoundException: If no instance found identified by ``item_id``.
        """

    @abstractmethod
    async def get(self, item_id: Any, **kwargs: Any) -> T:
        """Get instance identified by ``item_id``.

        Args:
            item_id: Identifier of the instance to be retrieved.

        Returns:
            The retrieved instance.

        Raises:
            RepositoryNotFoundException: If no instance found identified by ``item_id``.
        """

    @abstractmethod
    async def get_one(self, **kwargs: Any) -> T:
        """Get an instance if it exists or None.

        Args:
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances, after filtering applied.
        """

    @abstractmethod
    async def get_one_or_none(self, **kwargs: Any) -> T | None:
        """Get an instance if it exists or None.

        Args:
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances, after filtering applied.
        """

    @abstractmethod
    async def list(self, *filters: FilterTypes, **kwargs: Any) -> Sequence[T]:
        """Get a list of instances, optionally filtered.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances, after filtering applied.
        """

    @abstractmethod
    async def list_and_count(self, *filters: FilterTypes, **kwargs: Any) -> tuple[Sequence[T], int]:
        """List records with total count.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            Count of records returned by query, ignoring pagination.
        """

    @abstractmethod
    async def update(self, data: T) -> T:
        """Update instance with the attribute values present on `data`.

        Args:
            data: An instance that should have a value for `self.id_attribute` that exists in the
                collection.

        Returns:
            The updated instance.

        Raises:
            RepositoryNotFoundException: If no instance found with same identifier as `data`.
        """

    @abstractmethod
    async def update_many(self, data: Sequence[T]) -> Sequence[T]:
        """Update multiple instances with the attribute values present on instances in `data`.

        Args:
            data: A list of instance that should have a value for `self.id_attribute` that exists in the
                collection.

        Returns:
            The updated instances.

        Raises:
            RepositoryNotFoundException: If no instance found with same identifier as `data`.
        """

    @abstractmethod
    async def upsert(self, data: T) -> T:
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

    @abstractmethod
    def filter_collection_by_kwargs(self, collection: CollectionT, /, **kwargs: Any) -> CollectionT:
        """Filter the collection by kwargs.

        Has `AND` semantics where multiple kwargs name/value pairs are provided.

        Args:
            collection: the collection to be filtered
            **kwargs: key/value pairs such that objects remaining in the collection after filtering
                have the property that their attribute named `key` has value equal to `value`.

        Raises:
            RepositoryError: if a named attribute doesn't exist on `self.model_type`.
        """

    @staticmethod
    def check_not_found(item_or_none: T | None) -> T:
        """Raise `RepositoryNotFoundException` if `item_or_none` is `None`.

        Args:
            item_or_none: Item to be tested for existence.

        Returns:
            The item, if it exists.
        """
        if item_or_none is None:
            raise NotFoundError("No item found when one was expected")
        return item_or_none

    @classmethod
    def get_id_attribute_value(cls, item: T) -> Any:
        """Get value of attribute named as `self.id_attribute` on `item`.

        Args:
            item: Anything that should have an attribute named as `self.id_attribute` value.

        Returns:
            The value of attribute on `item` named as `self.id_attribute`.
        """
        return getattr(item, cls.id_attribute)

    @classmethod
    def set_id_attribute_value(cls, item_id: Any, item: T) -> T:
        """Return the ``item`` after the ID is set to the appropriate attribute.

        Args:
            item_id: Value of ID to be set on instance
            item: Anything that should have an attribute named as :attr:`id_attribute <AbstractRepository.id_attribute>` value.

        Returns:
            Item with ``item_id`` set to :attr:`id_attribute <AbstractRepository.id_attribute>`
        """
        setattr(item, cls.id_attribute, item_id)
        return item
