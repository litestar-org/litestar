from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from pymongo import ReturnDocument, UpdateOne

from litestar.contrib.mongodb_motor.repository._util import _convert_cursor_to_list_async, wrap_pymongo_exception
from litestar.contrib.repository import AbstractAsyncRepository, FilterTypes, NotFoundError, RepositoryError
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, SearchFilter

if TYPE_CHECKING:
    from collections import abc
    from datetime import datetime

    from motor.motor_asyncio import AsyncIOMotorCollection

DocumentType = Dict[str, Any]


class MongoDbMotorAsyncRepository(AbstractAsyncRepository[DocumentType]):
    """Motor based implementation of the repository interface."""

    id_attribute = "_id"
    model_type: type[DocumentType] = dict

    def __init__(
        self, collection: AsyncIOMotorCollection, **kwargs: Any  # pyright: ignore[reportGeneralTypeIssues]
    ) -> None:
        super().__init__(**kwargs)
        self.collection = collection

    async def add(self, data: DocumentType) -> DocumentType:
        """Add ``data`` to the collection.

        Args:
            data: Dictionary to be added to the collection.

        Returns:
            The added document.
        """
        with wrap_pymongo_exception():
            await self.collection.insert_one(data)
            return data

    async def add_many(self, data: list[DocumentType]) -> list[DocumentType]:
        """Add multiple dictionaries to the collection.

        Args:
            data: Iterable of dictionaries to be added to the collection.

        Returns:
            The added documents.
        """
        with wrap_pymongo_exception():
            await self.collection.insert_many(data)
            return data

        # ...

    async def count(
        self,
        *filters: FilterTypes,
        **kwargs: Any,
    ) -> int:
        """Count the number of documents in the collection matching the filters.

        Args:
            *filters: Filters to apply to the collection.
            **kwargs: Additional keyword arguments to filter the collection.

        Returns:
            The number of documents in the collection matching the filters.
        """

        query = self._build_query_from_filters(*filters)
        query.update(kwargs)
        # We type ignore here any because if we use cast then the sync version gets a redundant cast error
        return await self.collection.count_documents(query)  # type: ignore[no-any-return]

    async def delete(self, item_id: Any) -> DocumentType:
        """Delete instance identified by ``item_id``.

        Args:
            item_id: Identifier of instance to be deleted.

        Returns:
            The deleted instance.

        Raises:
            NotFoundError: If no instance found identified by ``item_id``.
        """
        with wrap_pymongo_exception():
            document = await self.collection.find_one_and_delete({self.id_attribute: item_id})
            self.check_not_found(document)
            return cast(DocumentType, document)

    async def delete_many(self, item_ids: list[Any]) -> list[DocumentType]:
        """Delete instance identified by ``item_id``.

        Args:
            item_ids: Identifier of instance to be deleted.

        Returns:
            The deleted instances.

        """
        with wrap_pymongo_exception():
            cursor = self.collection.find({self.id_attribute: {"$in": item_ids}})
            documents_to_delete = await self._convert_cursor_to_list(cursor)
            await self.collection.delete_many({self.id_attribute: {"$in": item_ids}})
            return documents_to_delete

    async def exists(self, **kwargs: Any) -> bool:
        """Return true if the object specified by ``kwargs`` exists.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            True if the instance was found. False if not found.

        """
        existing = await self.count(**kwargs)
        return existing > 0

    async def get(self, item_id: Any, **kwargs: Any) -> DocumentType:
        """Get instance identified by ``item_id``.

        Args:
            item_id: Identifier of the instance to be retrieved.
            **kwargs: Additional parameters

        Returns:
            The retrieved instance.

        Raises:
            NotFoundError: If no instance found identified by ``item_id``.
        """
        with wrap_pymongo_exception():
            document = await self.collection.find_one({self.id_attribute: item_id, **kwargs})
            self.check_not_found(document)
            return cast(DocumentType, document)

    async def get_one(self, **kwargs: Any) -> DocumentType:
        """Get instance identified by ``kwargs``.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            The retrieved instance.

        Raises:
            NotFoundError: If no instance found identified by `item_id`.
        """
        with wrap_pymongo_exception():
            document = await self.collection.find_one(kwargs)
            self.check_not_found(document)
            return cast(DocumentType, document)

    async def get_or_create(
        self, match_fields: list[str] | str | None = None, upsert: bool = True, **kwargs: Any
    ) -> tuple[DocumentType, bool]:
        """Get instance identified by ``kwargs`` or create if it doesn't exist.

        Args:
            match_fields: a list of keys to use to match the existing model.  When empty, all fields are matched.
            upsert: When using match_fields and actual model values differ from `kwargs`, perform an update operation on the model.
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            a tuple that includes the instance and whether it was newly created.
        """
        if isinstance(match_fields, str):
            match_fields = [match_fields]
        # KeyError is expected to be thrown if a match_field is not in field_values, not sure if this is the best way to handle this
        # Could also do a ".get" and then check for None but not sure if that is better since it would be a silent failure
        match_filter = kwargs if match_fields is None else {k: kwargs[k] for k in match_fields}

        doc = await self.get_one_or_none(**match_filter)

        if doc is None:
            doc = self.model_type(kwargs)
            c = await self.add(doc)
            return c, True

        if upsert:
            update = {"$set": kwargs}
            with wrap_pymongo_exception():
                return (
                    await self.collection.find_one_and_update(doc, update, return_document=ReturnDocument.AFTER),
                    False,
                )
        return doc, False

    async def get_one_or_none(self, **kwargs: Any) -> DocumentType | None:
        """Get instance identified by ``kwargs`` or None if not found.

        Args:
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            The retrieved instance or None
        """
        with wrap_pymongo_exception():
            return cast(Optional[DocumentType], await self.collection.find_one(kwargs))

    async def update(self, data: DocumentType) -> DocumentType:
        """Update instance with the attribute values present on ``data``.

        Args:
            data: An instance that should have a value for `self.id_attribute` that exists in the
                collection.

        Returns:
            The updated instance.

        Raises:
            NotFoundError: If no instance found with same identifier as ``data``.
        """
        with wrap_pymongo_exception():
            result = await self.collection.find_one_and_update(
                {self.id_attribute: self.get_id_attribute_value(data)},
                {"$set": data},
                return_document=ReturnDocument.AFTER,
            )
            self.check_not_found(result)
            return cast(DocumentType, result)

    async def update_many(self, data: list[DocumentType]) -> list[DocumentType]:
        """Update one or more instances with the attribute values present on ``data``.

        Args:
            data: A list of documents to update.  Each should have a value for `self.id_attribute` that exists in the
                collection.

        Returns:
            The updated instances.

        Raises:
            NotFoundError: If no instance found with same identifier as `data`.
        """

        bulk_operations = []

        for instance_data in data:
            _id = self.get_id_attribute_value(instance_data)
            bulk_operations.append(UpdateOne({"_id": _id}, {"$set": instance_data}))

        with wrap_pymongo_exception():
            result = await self.collection.bulk_write(bulk_operations)

            if result.matched_count != len(data):
                raise NotFoundError(
                    f"Some instances were not found and updated. Total data: {len(data)}, Matched: {result.matched_count}"
                )

            return data

    async def upsert(self, data: DocumentType) -> DocumentType:
        """Update or create instance.

        Updates instance with the attribute values present on `data`, or creates a new instance if
        one doesn't exist.

        Args:
            data: Instance to update existing, or be created. Identifier used to determine if an
                existing instance exists is the value of an attribute on `data` named as value of
                `self.id_attribute`.

        Returns:
            The updated or created instance.
        """
        _id = self.get_id_attribute_value(data)

        with wrap_pymongo_exception():
            document = await self.collection.find_one_and_update(
                {"_id": data["_id"]}, {"$set": data}, return_document=ReturnDocument.AFTER
            )
            return cast(DocumentType, document)

    async def list_and_count(self, *filters: FilterTypes, **kwargs: Any) -> tuple[list[DocumentType], int]:
        """List records with total count.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            Count of records returned by query, ignoring pagination.
        """
        query = self._build_query_from_filters(*filters)
        query.update(kwargs)

        with wrap_pymongo_exception():
            cursor = self.collection.find(query)
            docs = await self._convert_cursor_to_list(cursor)
            return docs, len(docs)

    async def _convert_cursor_to_list(self, cursor: Any) -> list[DocumentType]:
        return await _convert_cursor_to_list_async(cursor)

    async def list(self, *filters: FilterTypes, **kwargs: Any) -> list[DocumentType]:
        """Get a list of instances, optionally filtered.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances, after filtering applied.
        """
        query = self._build_query_from_filters(*filters)
        query.update(kwargs)

        with wrap_pymongo_exception():
            cursor = self.collection.find(query)
            return await self._convert_cursor_to_list(cursor)

    def filter_collection_by_kwargs(  # type:ignore[override]
        self,
        collection: dict[str, Any],
        /,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Filter the collection by kwargs.

        Args:
            collection: A dictionary representing the initial query.
            **kwargs: key/value pairs that should be added to the query.

        Returns:
            An updated query dictionary with additional filters.
        """

        collection.update(kwargs)
        return collection

    def _build_query_from_filters(self, *filters: FilterTypes) -> dict:
        """Build a query dictionary from the provided filters.

        Args:
            *filters: Filters to apply to the collection.

        Returns:
            A dictionary representing the query.
        """
        query = {}
        for filter_ in filters:
            if isinstance(filter_, BeforeAfter):
                query.update(
                    self._build_before_after_query(filter_.field_name, before=filter_.before, after=filter_.after)
                )
            elif isinstance(filter_, CollectionFilter):
                query.update(self._build_collection_filter_query(filter_.field_name, values=filter_.values))
            elif isinstance(filter_, SearchFilter):
                query.update(
                    self._build_search_filter_query(
                        filter_.field_name, value=filter_.value, ignore_case=bool(filter_.ignore_case)
                    )
                )
            else:
                raise RepositoryError(f"Unsupported filter type: {type(filter_)}")
        return query

    def _build_before_after_query(
        self, field_name: str, before: datetime | None, after: datetime | None
    ) -> dict[str, Any]:
        """Build a query dictionary from the provided ``BeforeAfter`` filter values.

        Args:
            field_name: Field name to filter on.
            before: Filter results where field earlier than this.
            after: Filter results where field later than this.

        Returns:
            A dictionary representing the query.
        """
        query: dict = {}
        if before:
            query[field_name] = {"$lt": before}
        if after:
            if field_name in query:
                query[field_name]["$gt"] = after
            else:
                query[field_name] = {"$gt": after}
        return query

    def _build_collection_filter_query(self, field_name: str, values: abc.Collection[Any]) -> dict:
        """Build a query dictionary from the provided ``CollectionFilter`` values.

        Args:
            field_name: Field name to filter on.
            values: Values for ``IN`` clause.

        Returns:
            A dictionary representing the query.
        """
        return {field_name: {"$in": values}}

    def _build_search_filter_query(self, field_name: str, value: str, ignore_case: bool) -> dict:
        """Build a query dictionary from the provided ``SearchFilter`` values.

        Args:
            field_name: Field name to filter on.
            value: Values for ``LIKE`` clause.
            ignore_case: Should the search be case-insensitive.

        Returns:
            A dictionary representing the query.
        """
        query = {field_name: {"$regex": value}}
        if ignore_case:
            query[field_name]["$options"] = "i"
        return query
