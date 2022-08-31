# middleware

::: starlite.middleware.MiddlewareProtocol
    options:
        members:
            - __init__
            - __call__

::: starlite.middleware.DefineMiddleware
    options:
        members:
            - __init__

::: starlite.middleware.AuthenticationResult
    options:
        members:
            - user
            - auth

::: starlite.middleware.AbstractAuthenticationMiddleware
    options:
        members:
            - scopes
            - error_response_media_type
            - websocket_error_status_code
            - create_error_response
            - authenticate_request

::: starlite.middleware.CSRFMiddleware
    options:
        members:
            - __init__

::: starlite.middleware.ExceptionHandlerMiddleware
    options:
        members:
            - __init__
            - default_http_exception_handler

::: starlite.middleware.CompressionMiddleware
    options:
        members:
            - __init__

::: starlite.middleware.compression.brotli.BrotliMode

::: starlite.middleware.compression.brotli.CompressionEncoding
    options:
        members:
            - GZIP
            - BROTLI

::: starlite.middleware.compression.brotli.BrotliMiddleware
    options:
        members:
            - __init__

::: starlite.middleware.compression.gzip.GZipMiddleware
    options:
        members:
            - __init__
