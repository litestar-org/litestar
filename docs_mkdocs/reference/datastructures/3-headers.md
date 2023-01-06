# Headers

::: starlite.datastructures.Headers
    options:
        members:
            - __init__
            - from_scope

::: starlite.datastructures.MutableScopeHeaders
    options:
        members:
            - __init__
            - add
            - getall
            - extend_header_value

::: starlite.datastructures.ResponseHeader
    options:
        members:
            - documentation_only
            - value

::: starlite.datastructures.headers.Header
    options:
        members:
            - documentation_only

::: starlite.datastructures.CacheControlHeader
    options:
        members:
            - max_age
            - s_maxage
            - no_cache
            - no_store
            - private
            - public
            - no_transform
            - must_revalidate
            - proxy_revalidate
            - must_understand
            - immutable
            - stale_while_revalidate
            - to_header
            - from_header
            - prevent_storing

::: starlite.datastructures.ETag
    options:
        members:
            - value
            - weak
