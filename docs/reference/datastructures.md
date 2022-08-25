# datastructures

::: starlite.datastructures.BackgroundTask
    options:
        members:
            - __init__

::: starlite.datastructures.BackgroundTasks
    options:
        members:
            - __init__

::: starlite.datastructures.State

::: starlite.datastructures.Cookie
    options:
        members:
            - key
            - value
            - max_age
            - expires
            - path
            - domain
            - secure
            - httponly
            - samesite
            - description
            - documentation_only
            - to_header

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

::: starlite.datastructures.Template
    options:
        members:
            - name
            - context
            - to_response

::: starlite.datastructures.ResponseHeader
    options:
        members:
            - documentation_only
            - value

::: starlite.datastructures.UploadFile
