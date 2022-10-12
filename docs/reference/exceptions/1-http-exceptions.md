# HTTP Exceptions

:::starlite.exceptions.HTTPException
    options:
        members:
            - __init__
            - detail
            - extra
            - headers
            - status_code

:::starlite.exceptions.ImproperlyConfiguredException

:::starlite.exceptions.InternalServerException
    options:
        members:
            - status_code

:::starlite.exceptions.MethodNotAllowedException
    options:
        members:
            - status_code

:::starlite.exceptions.NotAuthorizedException
    options:
        members:
            - status_code

:::starlite.exceptions.NoRouteMatchFoundException
    options:
        members:
            - status_code

:::starlite.exceptions.NotFoundException
    options:
        members:
            - status_code

:::starlite.exceptions.PermissionDeniedException
    options:
        members:
            - status_code

:::starlite.exceptions.ServiceUnavailableException

:::starlite.exceptions.TemplateNotFoundException
    options:
        members:
            - __init__

:::starlite.exceptions.TooManyRequestsException
    options:
        members:
            - status_code

:::starlite.exceptions.ValidationException
    options:
        members:
            - status_code
