# Pagination

When you need to return a large number of items from an endpoint it is common practice to use pagination to ensure
clients
can request a specific subset or "page" from the total dataset. Starlite supports three types of pagination out of the
box:

- classic pagination
- limit / offset pagination
- cursor pagination

## Classic Pagination

In classic pagination the dataset is divided into pages of a specific size and the consumer then requests a specific page.

```py title="Classic Pagination"
--8<-- "examples/datastructures/pagination/using_classic_pagination.py"
```

The data container for this pagination is
called [`ClassicPagination`][starlite.datastructures.pagination.ClassicPagination], which is what will be returned
by the paginator in the above example This will also generate the corresponding OpenAPI documentation.

If you require async logic, you can implement
the [`AbstractAsyncClassicPaginator`][starlite.datastructures.pagination.AbstractAsyncClassicPaginator] instead of
the [`AbstractSyncClassicPaginator`][starlite.datastructures.pagination.AbstractSyncClassicPaginator].


## Offset Pagination

In offset pagination the consumer requests a number of items specified by `limit` and the `offset` from the beginning of the dataset.
For example, given a list of 50 items, you could request `limit=10`, `offset=39` to request items 40-50.

```py title="Offset Pagination"
--8<-- "examples/datastructures/pagination/using_offset_pagination.py"
```

The data container for this pagination is
called [`OffsetPagination`][starlite.datastructures.pagination.OffsetPagination], which is what will be returned
by the paginator in the above example This will also generate the corresponding OpenAPI documentation.

If you require async logic, you can implement
the [`AbstractAsyncOffsetPaginator`][starlite.datastructures.pagination.AbstractAsyncOffsetPaginator] instead of
the [`AbstractSyncOffsetPaginator`][starlite.datastructures.pagination.AbstractSyncOffsetPaginator].


## Cursor Pagination

In cursor pagination the consumer requests a number of items specified by `results_per_page` and a `cursor` after which results are given.
Cursor is unique identifier within the dataset that serves as a way to point the starting position.

```py title="Cursor Pagination"
--8<-- "examples/datastructures/pagination/using_cursor_pagination.py"
```

The data container for this pagination is
called [`CursorPagination`][starlite.datastructures.pagination.CursorPagination], which is what will be returned
by the paginator in the above example This will also generate the corresponding OpenAPI documentation.

If you require async logic, you can implement
the [`AbstractAsyncCursorPaginator`][starlite.datastructures.pagination.AbstractAsyncCursorPaginator] instead of
the [`AbstractSyncCursorPaginator`][starlite.datastructures.pagination.AbstractSyncCursorPaginator].
