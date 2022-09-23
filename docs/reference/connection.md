# connection

::: starlite.connection.base.User

::: starlite.connection.base.Auth

::: starlite.connection.base.Handler

::: starlite.connection.base.ASGIConnection
    options:
        members:
            - __init__
            - app
            - auth
            - base_url
            - clear_session
            - client
            - cookies
            - headers
            - logger
            - path_params
            - query_params
            - route_handler
            - session
            - set_session
            - state
            - url
            - url_for
            - user

::: starlite.connection.request.Request
    options:
        members:
            - __init__
            - app
            - auth
            - base_url
            - body
            - clear_session
            - client
            - content_type
            - cookies
            - form
            - headers
            - json
            - logger
            - method
            - path_params
            - query_params
            - route_handler
            - send_push_promise
            - session
            - set_session
            - state
            - stream
            - url
            - url_for
            - user

::: starlite.connection.websocket.WebSocket
    options:
        members:
            - __init__
            - accept
            - app
            - auth
            - base_url
            - clear_session
            - client
            - close
            - cookies
            - headers
            - logger
            - path_params
            - query_params
            - receive_bytes
            - receive_data
            - receive_json
            - receive_text
            - route_handler
            - send_bytes
            - send_data
            - send_json
            - send_text
            - session
            - set_session
            - state
            - url
            - url_for
            - user
