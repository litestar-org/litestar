# JWT Security Backend

::: starlite.contrib.jwt.JWTAuth
    options:
        members:
            - algorithm
            - auth_header
            - authentication_middleware_class
            - default_token_expiration
            - dependencies
            - description
            - exclude
            - exclude_opt_key
            - guards
            - login
            - middleware
            - on_app_init
            - openapi_components
            - openapi_security_scheme_name
            - retrieve_user_handler
            - route_handlers
            - scopes
            - security_requirement
            - token_secret

::: starlite.contrib.jwt.JWTCookieAuth
    options:
        members:
            - algorithm
            - auth_header
            - authentication_middleware_class
            - default_token_expiration
            - dependencies
            - description
            - domain
            - exclude
            - exclude_opt_key
            - guards
            - key
            - login
            - middleware
            - on_app_init
            - openapi_components
            - openapi_security_scheme_name
            - path
            - retrieve_user_handler
            - route_handlers
            - samesite
            - scopes
            - secure
            - security_requirement
            - token_secret

::: starlite.contrib.jwt.OAuth2PasswordBearerAuth
    options:
        members:
            - algorithm
            - auth_header
            - authentication_middleware_class
            - default_token_expiration
            - dependencies
            - description
            - domain
            - exclude
            - exclude_opt_key
            - guards
            - key
            - login
            - middleware
            - oauth_scopes
            - on_app_init
            - openapi_components
            - openapi_security_scheme_name
            - path
            - retrieve_user_handler
            - route_handlers
            - samesite
            - scopes
            - secure
            - security_requirement
            - token_secret
            - token_url

::: starlite.contrib.jwt.Token
    options:
        members:
            - exp
            - iat
            - sub
            - iss
            - aud
            - jti
            - decode
            - encode

::: starlite.contrib.jwt.JWTAuthenticationMiddleware
    options:
        members:
            - __init__

::: starlite.contrib.jwt.JWTCookieAuthenticationMiddleware
    options:
        members:
            - __init__
