from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.contrib.mongodb_motor.repository._util import wrap_pymongo_exception
from litestar.contrib.mongodb_motor.repository.types import AsyncMotorCollection, Document
from litestar.contrib.repository import AbstractAsyncRepository, FilterTypes, RepositoryError
from litestar.contrib.repository.filters import BeforeAfter, CollectionFilter, SearchFilter

if TYPE_CHECKING:
    from collections import abc
    from datetime import datetime

    from pymongo.client_session import ClientSession
    from pymongo.collation import Collation


class MongoDbMotorAsyncRepository(AbstractAsyncRepository[Document]):
    def __init__(self, collection: AsyncMotorCollection, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.collection: AsyncMotorCollection = collection

    async def add(self, data: Document) -> Document:
        """Add `data` to the collection.

        Args:
            data: Dictionary to be added to the collection.

        Returns:
            The added dictionary with the `_id` field set if the operation was successfully acknowledged.
        """
        with wrap_pymongo_exception():
            result = await self.collection.insert_one(data)
            if result.acknowledged:
                data["_id"] = result.inserted_id
            return data

    async def add_many(self, data: list[Document]) -> list[Document]:
        """Add multiple dictionaries to the collection.

        Args:
            data: Iterable of dictionaries to be added to the collection.

        Returns:
            The added dictionaries with the `_id` field set if the operation was successfully acknowledged.
        """
        with wrap_pymongo_exception():
            result = await self.collection.insert_many(data)
            if result.acknowledged:
                for idx, doc in enumerate(data):
                    doc["_id"] = result.inserted_ids[idx]
            return data

        # ...

    async def count(
        self,
        *filters: FilterTypes,
        session: ClientSession | None = None,
        collation: Collation | None = None,
        **kwargs: Any,
    ) -> int:
        """Count the number of documents in the collection matching the filters.

        Args:
            *filters: Filters to apply to the collection.
            session: Optional session to use for the operation.
            collation: Optional collation to use for the operation.
            **kwargs: Optional keyword arguments to pass to the underlying `count_documents` method.

        Returns:
            The number of documents in the collection matching the filters.
        """

        query = self._build_query(*filters)
        query = self._apply_kwargs_to_query(query, **kwargs)
        count = await self.collection.count_documents(query, session=session, collation=collation)
        return int(count)

    def _build_query(self, *filters: FilterTypes) -> dict:
        """Build a query dictionary from the provided filters.

        Args:
            *filters: Filters to apply to the collection.

        Returns:
            A dictionary representing the query.
        """
        query: dict = {}
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

    def _build_before_after_query(self, field_name: str, before: datetime | None, after: datetime | None) -> dict:
        """Build a query dictionary from the provided `BeforeAfter` filter values.

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
            query[field_name] = {"$gt": after}
        return query

    def _build_collection_filter_query(self, field_name: str, values: abc.Collection[Any]) -> dict:
        """Build a query dictionary from the provided `CollectionFilter` values.

        Args:
            field_name: Field name to filter on.
            values: Values for `IN` clause.

        Returns:
            A dictionary representing the query.
        """
        return {field_name: {"$in": values}}

    def _build_search_filter_query(self, field_name: str, value: str, ignore_case: bool) -> dict:
        """Build a query dictionary from the provided `SearchFilter` values.

        Args:
            field_name: Field name to filter on.
            value: Values for `LIKE` clause.
            ignore_case: Should the search be case-insensitive.

        Returns:
            A dictionary representing the query.
        """
        return {field_name: {"$regex": value, "$options": "i" if ignore_case else ""}}

    def _apply_kwargs_to_query(self, query: dict, **kwargs: Any) -> dict:
        """Apply keyword arguments to the query.

        Args:
            query: Query to apply the keyword arguments to.
            **kwargs: Keyword arguments to apply to the query.

        Returns:
            The updated query.
        """
        for key, value in kwargs.items():
            query[key] = value
        return query
