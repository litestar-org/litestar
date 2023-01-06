# Test Client

::: starlite.testing.TestClient
    options:
        members:
            - __init__
            - __enter__
            - request
            - get
            - post
            - patch
            - put
            - delete
            - options
            - head
            - set_session_data
            - get_session_data
            - portal

::: starlite.testing.test_client.WebSocketTestSession
    options:
        members:
            - close
            - receive
            - receive_bytes
            - receive_json
            - receive_text
            - send
            - send_bytes
            - send_json
            - send_text

::: starlite.testing.create_test_client
    options:
        separate_signature: false  # black fails to format
