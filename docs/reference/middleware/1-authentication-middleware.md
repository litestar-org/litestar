# Authentication Middleware

::: starlite.middleware.AuthenticationResult
    options:
        members:
            - user
            - auth

::: starlite.middleware.AbstractAuthenticationMiddleware
    options:
        members:
            - __init__
            - scopes
            - error_response_media_type
            - websocket_error_status_code
            - create_error_response
            - authenticate_request
