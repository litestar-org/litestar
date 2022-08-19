# middleware

::: starlite.middleware.base.MiddlewareProtocol
    options:
        members:
            - __init__

::: starlite.middleware.base.DefineMiddleware
    options:
        members:
            - __init__

::: starlite.middleware.authentication.AuthenticationResult
    options:
        members:
            - user
            - auth

::: starlite.middleware.csrf.CSRFMiddleware
    options:
        members:
            - __init__

::: starlite.middleware.exceptions.ExceptionHandlerMiddleware
    options:
        members:
            - __init__

::: starlite.middleware.authentication.AbstractAuthenticationMiddleware
    options:
        members:
            - scopes
            - error_response_media_type
            - websocket_error_status_code
            - __init__
            - create_error_response
            - authenticate_request

::: starlite.middleware.compression.brotli.BrotliMode
    options:
        members:
            - GENERIC
            - TEXT
            - FONT

::: starlite.middleware.compression.brotli.BrotliMiddleware
    options:
        show_source: false
        members:
            - __init__
