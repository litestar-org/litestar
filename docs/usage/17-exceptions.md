# Exceptions and Exception Handling

Starlite define a base error called `StarliteException` which serves as a basis to all other exceptions.

In general, Starlite will raise two types of exceptions - exceptions that arise during application init, which fall
under the broad scope of configurations errors, and exceptions that are raised as part of the normal application flow,
i.e. exceptions in route handlers, dependencies and middleware that should be serialized in some fashion.

## Configuration Exceptions

For missing extra dependencies, Starlite will raise either `MissingDependencyException`. For example, if you try to use
the `SQLAlchemyPLugin` without having SQLAlchemy installed, this will be raised when you start the application.

For other configuration issues, Starlite will raise `ImproperlyConfiguredException` with a message explaining the issue.

## Application Exceptions

For application exceptions, Starlite uses the class `HTTPException`, which inherits from both `StarliteException`
and `starlette.exceptions.HTTPException`. This class receives three
optional kwargs:

- `detail`: The error message. Defaults to the "phrase" of the status code using `http.HttpStatus`.
- `status_code`: A valid HTTP error status code (4xx or 5xx range). Defaults to 500.
- `extra`: Either a dictionary or a list of of arbitrary values.

The default exception handler will serialize `HTTPExceptions` into a json response with the following structure:

```json
{
  "status_code": 500,
  "detail": "Internal Server Error",
  "extra": {}
}
```

Starlite also offers several pre-configured **exception subclasses** with pre-set error codes that you can use:

- `ImproperlyConfiguredException`: status code 500. Used internally for configuration errors.
- `ValidationException`: status code 400. This is the exception raised when validation or parsing fails.
- `NotFoundException`: status code 404.
- `NotAuthorizedException`: status code 401.
- `PermissionDeniedException`: status code 403.
- `InternalServerException`: status code 500.
- `ServiceUnavailableException`: status code 503.

When a value fails `pydantic` validation, the result will be a `ValidationException` with the `extra` key set to the
pydantic validation errors. Thus this data will be made available for the API consumers by default.

## Exception Handling

Starlite handles all errors by default by transforming them into **JSON responses**. If the errors are **instances of**
either the `starlette.exceptions.HTTPException` or the `starlite.exceptions.HTTPException`, the responses will include
the appropriate `status_code`. Otherwise, the responses will **default to 500** - "Internal Server Error".

You can **customize exception handling** by passing a dictionary – mapping either `error status codes`,
or `exception classes`, to callables. For example, if you would like to replace the default exception handler with a
handler that returns plain-text responses you could do this:

```python
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlite import HTTPException, MediaType, Request, Response, Starlite


def plain_text_exception_handler(_: Request, exc: Exception) -> Response:
    """Default handler for exceptions subclassed from HTTPException"""
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    detail = ""
    if hasattr(exc, "detail"):
        detail = exc.detail
    if hasattr(exc, "status_code"):
        status_code = exc.status_code
    return Response(
        media_type=MediaType.TEXT,
        content=detail,
        status_code=status_code,
    )


app = Starlite(
    route_handlers=[...],
    exception_handlers={HTTPException: plain_text_exception_handler},
)
```

The above will define a top level exception handler that will apply the `plain_text_exception_handler` function to all
exceptions that inherit from `HTTPException`. You could of course be more granular:

```python
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlite import ValidationException, Request, Response, Starlite


def first_exception_handler(request: Request, exc: Exception) -> Response:
    ...


def second_exception_handler(request: Request, exc: Exception) -> Response:
    ...


def third_exception_handler(request: Request, exc: Exception) -> Response:
    ...


app = Starlite(
    route_handlers=[...],
    exception_handlers={
        ValidationException: first_exception_handler,
        HTTP_500_INTERNAL_SERVER_ERROR: second_exception_handler,
        ValueError: third_exception_handler,
    },
)
```

The choice whether to use a single function that has switching logic inside it, or multiple functions depends on your
specific needs.

While it does not make much sense to have different functions with a top-level exception handling,
Starlite supports defining exception handlers on all levels of the app, with the lower levels overriding levels above
them. Thus, in the following example, the exception handler for the route handler function will handle
the `ValidationException` related to it:

```python
from starlite import (
    HTTPException,
    ValidationException,
    Request,
    Response,
    Starlite,
    get,
)


def top_level_handler(request: Request, exc: Exception) -> Response:
    ...


def handler_level_handler(request: Request, exc: Exception) -> Response:
    ...


@get("/greet", exception_handlers={ValidationException: top_level_handler})
def my_route_handler(name: str) -> str:
    return f"hello {name}"


app = Starlite(
    route_handlers=[my_route_handler],
    exception_handlers={HTTPException: top_level_handler},
)
```

### Exception Handling Layers

Since Starlite allows users to define both exception handlers and middlewares in a layered fashion, i.e. on individual
route handlers, controllers, routers or the app layer, multiple layers of exception handlers are required to ensure that
exceptions are handled correctly:

<figure markdown>
  ![Exception Handlers' Structure](img/exception-handlers.jpg){ width="500" }
  <figcaption>Exception Handlers</figcaption>
</figure>

Because of the above structure, the exceptions raised by the ASGI Router itself, namely `404 Not Found`
and `405 Method Not Allowed` are handled only by exception handlers defined on the app layer. Thus if you want to affect
these exceptions, you will need to pass the exception handlers for them to the Starlite constructor and cannot use other
layers for this purpose.

### Examples

#### Logging Exception Handler

<!-- prettier-ignore -->
!!! note
    `starlite.exceptions.utils.create_exception_response()` is used internally to produce default error responses if no
    handler has been registered to a route. This is available as part of the public API of Starlite so that you can
    apply it wherever necessary to ensure consistent error responses across your application.

```python
import logging
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.responses import Response
from starlite.exceptions.utils import create_exception_response
from starlite.types import Request
from starlite import Starlite

logger = logging.getLogger(__name__)


def logging_exception_handler(request: Request, exc: Exception) -> Response:
    """
    Logs exception and returns appropriate response.

    Parameters
    ----------
    request : Request
        The request that caused the exception.
    exc :
        The exception caught by the Starlite exception handling middleware and passed to the
        callback.

    Returns
    -------
    Response
    """
    logger.error("Application Exception", exc_info=exc)
    return create_exception_response(exc)


app = Starlite(
    ...,
    exception_handlers={HTTP_500_INTERNAL_SERVER_ERROR: logging_exception_handler},
)
```
