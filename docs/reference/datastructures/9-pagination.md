# Pagination Containers

::: starlite.datastructures.CursorPagination
    options:
        members:
            - items
            - results_per_page
            - cursor

::: starlite.datastructures.LimitOffsetPagination
    options:
        members:
            - items
            - limit
            - offset
            - total

::: starlite.datastructures.AbstractCursorPaginator
    options:
        members:
            - get_items
            - get_paginated_data

::: starlite.datastructures.AbstractLimitOffsetPaginator
    options:
        members:
            - get_total
            - get_items
            - get_paginated_data
