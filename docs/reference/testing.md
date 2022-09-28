# testing

::: starlite.testing.TestClient
    options:
        members:
            - __init__
            - __enter__

::: starlite.testing.create_test_client
    options:
        separate_signature: false  # black fails to format

::: starlite.testing.RequestFactory
    options:
        members:
            - __init__
            - get
            - post
            - put
            - patch
            - delete
