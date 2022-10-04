# Session Middleware

::: starlite.middleware.session.SessionCookieConfig
    options:
        members:
            - domain
            - httponly
            - key
            - max_age
            - middleware
            - path
            - samesite
            - scopes
            - secret
            - secure

::: starlite.middleware.session.SessionMiddleware
    options:
        members:
            - __init__
            - dump_data
            - load_data
