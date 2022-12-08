# Enums

::: starlite.enums.HttpMethod
    options:
        members:
            - DELETE
            - GET
            - HEAD
            - OPTIONS
            - PATCH
            - POST
            - PUT

::: starlite.enums.MediaType
    options:
        members:
            - HTML
            - JSON
            - TEXT
            - MESSAGEPACK

::: starlite.enums.OpenAPIMediaType
    options:
        members:
            - OPENAPI_JSON
            - OPENAPI_YAML

::: starlite.enums.RequestEncodingType
    options:
        members:
            - JSON
            - MULTI_PART
            - URL_ENCODED

::: starlite.enums.ScopeType
    options:
        members:
            - HTTP
            - WEBSOCKET
            - ASGI

::: starlite.enums.ParamType
    options:
        members:
            - PATH
            - QUERY
            - COOKIE
            - HEADER

::: starlite.enums.CompressionEncoding
    options:
        members:
            - GZIP
            - BROTLI
