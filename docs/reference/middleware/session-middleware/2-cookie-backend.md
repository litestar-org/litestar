# Cookie Backend

::: starlite.middleware.session.cookie_backend.CookieBackendConfig
    options:
        members:
            - secret

::: starlite.middleware.session.cookie_backend.CookieBackend
    options:
        members:
            - __init__
            - dump_data
            - load_data
            - get_cookie_keys
            - store_in_message
            - load_from_connection
