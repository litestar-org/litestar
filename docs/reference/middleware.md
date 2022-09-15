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

::: starlite.middleware.session.SessionCookieConfig
    options:
        members:
            - secret
            - key
            - max_age
            - scopes
            - path
            - domain
            - secure
            - httponly
            - samesite
            - middleware

::: starlite.middleware.session.SessionMiddleware
    options:
        members:
            - __init__
            - dump_data
            - load_data

::: starlite.middleware.rate_limit.RateLimitConfig
    options:
        members:
            - rate_limit
            - exclude
            - check_throttle_handler
            - middleware_class
            - set_rate_limit_headers
            - rate_limit_policy_header_key
            - rate_limit_remaining_header_key
            - rate_limit_reset_header_key
            - rate_limit_limit_header_key
            - cache_key_builder
            - middleware

::: starlite.middleware.rate_limit.RateLimitMiddleware
    options:
        members:
            - __init__
            - cache_key_from_request
            - retrieve_cached_history
            - set_cached_history
            - should_check_request
            - create_response_headers
