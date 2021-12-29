# Middleware

Middlewares are mini ASGI apps that receive the raw request object validate or transform it in some manner. The use for
middleware is when you need to operate on all incoming requests on the app level.

Starlite builds on top of the [Starlette middleware architecture](https://www.starlette.io/middleware/) and is 100%
compatible with it - and the 3rd party middleware created for it as well.

## The Middleware Protocol

You can build your own middleware by either subclassing the `starlette.middleware.base.BaseMiddleware` class (see the
starlette documentation), or by creating a class that implements the Starlite `MiddlewareProtocol`.

For example, lets create a simple middleware that does some naive logging for every request:

```python
import logging

from starlette.types import ASGIApp, Receive, Scope, Send
from starlite import MiddlewareProtocol, Request

logger = logging.getLogger(__name__)


class MyRequestLoggingMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ["http", "websocket"]:
            request = Request(scope)
            logger.log("%s - %s", request.method, request.url)
        await self.app(scope, receive, send)
```

What's happening above?

The `__init__` receives and sets "app" - app is not Starlite, but rather the next middleware in the stack, which is also
an ASGI app.

The `__call__` method makes this class into a `callable`, i.e. once instantiated this class acts like a function.

The three parameters, `scope, receive, send` are specified
by [the ASGI specification](https://asgi.readthedocs.io/en/latest/index.html).

Whats important to note here are two things:

1. Although scope is used to create an instance of request by passing it to the Request constructor, which makes it
   simpler to access because it does some parsing for you already, the actual source of truth is Scope - not the
   request. If you need to modify the data of the request you must modify the scope dictionary, not any ephemeral
   request objects created as in the above.
2. Once the middleware finishes doing whatever its doing, it should pass scope, receive and send to self.app - this is
   equivalent in other middleware architectures to calling `next`, which is what happens in the last line of the
   example.

## Built-in Middlewares

Starlette includes several builtin middlewares - you can see the list in the Starlette docs. Of these middlewares,
Starlite offers a simple way to use two of them:

### CORS

CORS ([Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)) is a common security
mechanism - that is often implemented using middleware. To enable CORS in a starlite application simple pass an instance
of `starlite.config.CORSConfig` to the Starlite constructor:

```python
from starlite import CORSConfig, Starlite

cors_config = CORSConfig(allow_origins=["https://www.example.com"])

app = Starlite(route_handlers=[...], cors_config=cors_config)
```

You can pass the following kwargs to CORSConfig:

* `allow_origins`: list of domain schemas, defaults to `["*"]`
* `allow_methods`: list of http methods, defaults to `["*"]`
* `allow_headers`: list of header keys, defaults to `["*"]`
* `allow_credentials`: A boolean dictating whether CORS should support cookies in cross-origin requests. Defaults
  to `False`.
* `allow_origin_regex`: A regex string that is matches against incoming request origins. Defaults to `None`.
* `expose_headers`: A list of response headers to expose. Defaults to `[]`.
* `max_age`: Sets a response header instructing the max amount of _seconds_ that the browser should cache a CORS
  response. Defaults to 600.

!!! note
    The asteriks symbol in the above kwargs means "match any".

You can read more about this middleware in the [starlette docs](https://www.starlette.io/middleware/#corsmiddleware).

### Trusted Hosts

Another common security mechanism is to require that each incoming request has a "HOST" header, and then to restrict
hosts to a specific set of domains. To enable this middleware simple pass a list of trusted hosts to the Starlite
constructor:

```python
from starlite import Starlite

app = Starlite(
    request_handlers=[...], allowed_hosts=["*.example.com", "www.wikipedia.org"]
)
```

You can use `*` to match any subdomains, as in the above.
