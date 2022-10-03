# Response Containers

::: starlite.datastructures.ResponseContainer
    options:
        members:
            - background
            - headers
            - cookies
            - to_response

::: starlite.datastructures.File
    options:
        members:
            - path
            - filename
            - stat_result
            - to_response

::: starlite.datastructures.Redirect
    options:
        members:
            - path
            - to_response

::: starlite.datastructures.Stream
    options:
        members:
            - iterator
            - to_response
