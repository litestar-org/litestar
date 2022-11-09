# Returning Responses

While the default response handling fits most use cases, in some cases you need to be able to return a response instance
directly.

Starlite allows you to return any class inheriting from the [`Response`][starlite.response.Response] class. Thus, the below
example will work perfectly fine:

```python
--8 < --"examples/responses/returning_responses.py"
```

!!! important
    In the case of the builtin [`TemplateResponse`][starlite.response.TemplateResponse],
    [`FileResponse`][starlite.response.FileResponse], [`StreamingResponse`][starlite.response.StreamingResponse] and
    [`RedirectResponse`][starlite.response.RedirectResponse] you should use the response "response containers", otherwise
    OpenAPI documentation will not be generated correctly. For more details see the respective documentation sections
    for the [Template](9-template-responses.md), [File](7-file-responses.md), [Stream](8-streaming-responses.md)
    and [Redirect](6-redirect-responses.md).

## Annotating Responses

As you can see above, the [`Response`][starlite.response.Response] class accepts a generic argument. This allows Starlite
to infer the response body when generating the OpenAPI docs.

!!! note
    If the generic argument is not provided, and thus defaults to `Any`, the OpenAPI docs will be imprecise. So make sure
    to type this argument even when returning an empty or `null` body, i.e. use `None`.

## Returning ASGI Applications

Starlite also supports returning ASGI applications directly, as you would responses. For example:

```python
from starlite import get
from starlite.types import ASGIApp, Receive, Scope, Send


@get("/")
def handler() -> ASGIApp:
    async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
        ...

    return my_asgi_app
```

### What is an ASGI Application?

An ASGI application in this context is any async callable (function, class method or simply a class that implements
that special `__call__` dunder method) that accepts the three ASGI arguments: `scope`, `receive` and `send`.

For example, all the following examples are ASGI applications:

#### Function ASGI Application

```python
from starlite.types import Receive, Scope, Send


async def my_asgi_app_function(scope: Scope, receive: Receive, send: Send) -> None:
    # do something here
    ...
```

#### Method ASGI Application

```python
from starlite.types import Receive, Scope, Send


class MyClass:
    async def my_asgi_app_method(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        # do something here
        ...
```

#### Class ASGI Application

```python
from starlite.types import Receive, Scope, Send


class ASGIApp:
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # do something here
        ...
```

### Returning Other Library Responses

Because you can return any ASGI Application from a route handler, you can also use any ASGI application from other
libraries. For example, you can return the response classes from Starlette or FastAPI directly from route handlers:

```python
from starlette.responses import JSONResponse

from starlite import get
from starlite.types import ASGIApp


@get("/")
def handler() -> ASGIApp:
    return JSONResponse(content={"hello": "world"})  # type: ignore
```

!!! important
    Starlite offers strong typing for the ASGI arguments. Other libraries often offer less strict typing, which might
    cause type checkers to complain when using ASGI apps from them inside Starlite.
    For the time being, the only solution is to add `# type: ignore` comments in the pertinent places.
    Nonetheless, the above example will work perfectly fine.
