# Using MiddlewareProtocol

The `starlite.middleware.base.MiddlewareProtocol` class is a [PEP 544 Protocol](https://peps.python.org/pep-0544/) that
specifies the minimal implementation of a middleware as follows:

```python
from typing import Protocol, Any
from starlette.types import ASGIApp, Scope, Receive, Send


class MiddlewareProtocol(Protocol):
    def __init__(self, app: ASGIApp, **kwargs: dict[str, Any]):
        ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        ...
```

The `__init__` method receives and sets "app". _It's important to understand_ that app is not an instance of Starlite in
this case, but rather the next middleware in the stack, which is also an ASGI app.

The `__call__` method makes this class into a `callable`, i.e. once instantiated this class acts like a function, that
has the signature of an ASGI app: The three parameters, `scope, receive, send` are specified
by [the ASGI specification](https://asgi.readthedocs.io/en/latest/index.html), and their values originate with the ASGI
server (e.g. _uvicorn_) used to run Starlite.

To use this protocol as a basis, simply subclass it - as you would any other class, and implement the two methods it
specifies:

```python
import logging

from starlette.types import ASGIApp, Receive, Scope, Send
from starlite import Request
from starlite.middleware.base import MiddlewareProtocol

logger = logging.getLogger(__name__)


class MyRequestLoggingMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            request = Request(scope)
            logger.info("%s - %s" % request.method, request.url)
        await self.app(scope, receive, send)
```

!!! important
Although `scope` is used to create an instance of request by passing it to the `Request` constructor, which makes it
simpler to access because it does some parsing for you already, the actual source of truth remains `scope` - not the
request. If you need to modify the data of the request you must modify the scope object, not any ephemeral request
objects created as in the above.

## Responding using the MiddlewareProtocol

Once a middleware finishes doing whatever its doing, it should pass `scope`, `receive` and `send` to an ASGI app and
await it. This is what's happening in the above example with : `await self.app(scope, receive, send)`. Let's explore
another example - redirecting the request to a different url from a middleware:

```python
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import RedirectResponse
from starlette.status import HTTP_307_TEMPORARY_REDIRECT
from starlite import Request
from starlite.middleware.base import MiddlewareProtocol


class RedirectMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if Request(scope).session is None:
            response = RedirectResponse(
                url="/login", status_code=HTTP_307_TEMPORARY_REDIRECT
            )
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

As you can see in the above, given some condition (request.session being None) we create a `RedirectResponse` and then
await it. Otherwise, we await `self.app`

## Modifying ASGI Requests and Responses using the MiddlewareProtocol

!!! important
If you'd like to modify a [Response](../../5-responses/0-responses-intro.md) object after it was created for a route
handler function but before the actual response message is transmitted, the correct place to do this is using the
special life-cycle hook called [After Request](../../13-lifecycle-hooks.md#After Request). The instructions in this
section are for how to modify the ASGI response message itself, which is a step further in the response process.

Using the `MiddlewareProtocol` you can intercept and modifying both the incoming and outgoing data in a request /
response cycle by "wrapping" that respective `receive` and `send` ASGI functions.

To demonstrate this, lets say we want to append a header with a timestamp to all outgoing responses. We could achieve
this by doing the following:

```python
import time

from starlette.datastructures import MutableHeaders
from starlette.types import Message, Receive, Scope, Send
from starlite.middleware.base import MiddlewareProtocol
from starlite.types import ASGIApp


class ProcessTimeHeader(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            start_time = time.time()

            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    process_time = time.time() - start_time
                    headers = MutableHeaders(scope=message)
                    headers.append("X-Process-Time", str(process_time))
                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)
```
