# Pagination Containers

::: starlite.datastructures.ClassicPagination
    options:
        members:
            - items
            - page_size
            - current_page
            - total_pages

::: starlite.datastructures.OffsetPagination
    options:
        members:
            - items
            - limit
            - offset
            - total

::: starlite.datastructures.CursorPagination
    options:
        members:
            - items
            - results_per_page
            - cursor


::: starlite.datastructures.AbstractSyncClassicPaginator
    options:
        members:
            - __call__
            - get_items
            - get_total

::: starlite.datastructures.AbstractAsyncClassicPaginator
    options:
        members:
            - __call__
            - get_items
            - get_total

::: starlite.datastructures.AbstractSyncOffsetPaginator
    options:
        members:
            - __call__
            - get_items
            - get_total

::: starlite.datastructures.AbstractAsyncOffsetPaginator
    options:
        members:
            - __call__
            - get_items
            - get_total

::: starlite.datastructures.AbstractSyncCursorPaginator
    options:
        members:
            - __call__
            - get_items

::: starlite.datastructures.AbstractAsyncCursorPaginator
    options:
        members:
            - __call__
            - get_items
