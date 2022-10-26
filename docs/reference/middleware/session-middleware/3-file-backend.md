# File backend

::: starlite.middleware.session.file_backend.FileBackendConfig
    options:
        members:
            - storage_path

::: starlite.middleware.session.file_backend.FileBackend
    options:
        members:
            - __init__
            - get
            - set
            - delete
            - delete_all
            - delete_expired
