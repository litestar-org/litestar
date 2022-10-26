# Base backend

::: starlite.middleware.session.base.BaseBackendConfig
    options:
        members:
            - key
            - max_age
            - scopes
            - path
            - domain
            - secure
            - httponly
            - samesite
            - middleware

::: starlite.middleware.session.base.ServerSideSessionConfig
    options:
        members:
            - session_id_bytes

::: starlite.middleware.session.base.SessionBackend
    options:
        members:
            - __init__
            - serialise_data
            - deserialise_data
            - store_in_message
            - load_from_connection

::: starlite.middleware.session.base.ServerSideBackend
    options:
        members:
            - __init__
            - store_in_message
            - load_from_connection
            - get
            - set
            - delete
            - delete_all
            - generate_session_id
