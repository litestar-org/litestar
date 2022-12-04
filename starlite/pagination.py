from abc import ABC, abstractmethod
from dataclasses import dataclass
from inspect import isawaitable
from typing import TYPE_CHECKING, Generic, List, Optional, Tuple, TypeVar
from uuid import UUID

T = TypeVar("T")
C = TypeVar("C", int, str, UUID)

if TYPE_CHECKING:
    from starlite.types import SyncOrAsyncUnion


@dataclass
class LimitOffsetPagination(Generic[T]):
    """Container for data returned using limit/offset pagination."""

    __slots__ = ("items", "limit", "offset", "total")

    items: List[T]
    """
    List of data being sent as part of the response.
    """
    limit: int
    """
    Maximal number of items to send.
    """
    offset: int
    """
    Offset from the beginning of the query. Identical to an index.
    """
    total: int
    """
    Total number of items.
    """


@dataclass
class CursorPagination(Generic[C, T]):
    """Container for data returned using cursor pagination."""

    __slots__ = ("items", "results_per_page", "cursor", "next_cursor")

    items: List[T]
    """
    List of data being sent as part of the response.
    """
    results_per_page: int
    """
    Maximal number of items to send.
    """
    cursor: Optional[C]
    """
    Unique ID, designating the last identifier in the given data set. This value can be used to request the "next" batch of records.
    """


class AbstractLimitOffsetPaginator(ABC, Generic[T]):
    """Base paginator class for limit / offset pagination.

    Implement this class to return paginated result sets using the limit / offset pagination scheme.
    """

    @abstractmethod
    def get_total(self) -> "SyncOrAsyncUnion[int]":
        """Return the total number of records.

        Returns:
            An integer - can be an awaitable.
        """
        raise NotImplementedError

    @abstractmethod
    def get_items(self, limit: int, offset: int) -> "SyncOrAsyncUnion[List[T]]":
        """Return a list of items of the given size 'limit' starting from position 'offset'.

        Args:
            limit: Maximal number of records to return.
            offset: Starting position within the result set (assume index 0 as starting position).

        Returns:
            A list or awaitable list of items.
        """
        raise NotImplementedError

    async def get_paginated_data(self, limit: int, offset: int) -> LimitOffsetPagination[T]:
        """Return a paginated result set.

        Args:
            limit: Maximal number of records to return.
            offset: Starting position within the result set (assume index 0 as starting position).

        Returns:
            A paginated result set.
        """
        total = self.get_total()

        if isawaitable(total):
            total = await total

        items = self.get_items(limit=limit, offset=offset)
        if isawaitable(items):
            items = await items

        return LimitOffsetPagination[T](items=items, total=total, offset=offset, limit=limit)  # type: ignore


class AbstractCursorPaginator(ABC, Generic[C, T]):
    """Base paginator class for cursor pagination.

    Implement this class to return paginated result sets using the cursor pagination scheme.
    """

    @abstractmethod
    def get_items(self, cursor: Optional[C], results_per_page: int) -> "SyncOrAsyncUnion[Tuple[List[T], Optional[C]]]":
        """Return a list of items of the size 'results_per_page' following the given cursor, if any,

        Args:
            cursor: A unique identifier that acts as the 'cursor' after which results should be given.
            results_per_page: A maximal number of results to return.

        Returns:
            A tuple containing the result set and a new cursor that marks the last record retrieved.
            The new cursor can be used to ask for the 'next_cursor' batch of results. The return value can be an awaitable.
        """
        raise NotImplementedError

    async def get_paginated_data(self, cursor: Optional[C], results_per_page: int) -> CursorPagination[C, T]:
        """Return a paginated result set given an optional cursor (unique ID) and a maximal number of results to return.

        Args:
            cursor: A unique identifier that acts as the 'cursor' after which results should be given.
            results_per_page: A maximal number of results to return.

        Returns:
            A paginated result set.
        """
        results = self.get_items(cursor=cursor, results_per_page=results_per_page)

        if isawaitable(results):
            results = await results

        items, new_cursor = results  # type: ignore

        return CursorPagination[C, T](
            items=items,
            results_per_page=results_per_page,
            cursor=new_cursor,
        )
