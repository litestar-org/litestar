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
            - client
            - cookies
            - headers
            - path_params
            - query_params
            - route_handler
            - session
            - state
            - url
            - user
            - clear_session
            - set_session
            - url_for

::: starlite.connection.request.Request
    options:
        members:
            - __init__
            - app
            - auth
            - base_url
            - body
            - client
            - content_type
            - cookies
            - form
            - headers
            - json
            - method
            - path_params
            - query_params
            - route_handler
            - session
            - state
            - stream
            - url
            - user
            - clear_session
            - send_push_promise
            - set_session
            - url_for

::: starlite.connection.websocket.WebSocket
    options:
        members:
            - __init__
            - app
            - auth
            - base_url
            - client
            - cookies
            - headers
            - path_params
            - query_params
            - route_handler
            - session
            - state
            - url
            - user
            - accept
            - clear_session
            - close
            - receive_bytes
            - receive_data
            - receive_json
            - receive_text
            - send_bytes
            - send_data
            - send_json
            - send_text
            - set_session
            - url_for
