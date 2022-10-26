# Redis backend

::: starlite.middleware.session.redis_backend.RedisBackendConfig
    options:
        members:
            - redis

::: starlite.middleware.session.redis_backend.RedisBackend
    options:
        members:
            - __init__
            - get
            - set
            - delete
            - delete_all
