# Middleware

Middlewares are mini ASGI apps that receive the raw request object and validate or transform it in some manner.

## The Middleware Protocol

<!-- prettier-ignore -->
!!! important
    Starlite allows users to use [Starlette Middleware](https://www.starlette.io/middleware/) and any 3rd
    party middlewares created for it, while offering its own middleware protocol as well.

You can build your own middleware by either subclassing the `starlette.middleware.base.BaseHTTPMiddleware` class (see
the starlette documentation), or by creating a class that implements the Starlite `MiddlewareProtocol`.

For example, lets create a simple middleware that does some naive logging for every request:

```python
import logging

from starlette.types import ASGIApp, Receive, Scope, Send
from starlite import MiddlewareProtocol, Request

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

What's happening above?

The `__init__` method receives and sets "app" - app is not an instance of Starlite, but rather the next middleware in
the stack, which is also an ASGI app.

The `__call__` method makes this class into a `callable`, i.e. once instantiated this class acts like a function, that
has the signature of an ASGI app: The three parameters, `scope, receive, send` are specified
by [the ASGI specification](https://asgi.readthedocs.io/en/latest/index.html), and their values originate with the ASGI
server (e.g. _uvicorn_) used to run Starlite.

It's important to note here two things:

1. Although `scope` is used to create an instance of request by passing it to the `Request` constructor, which makes it
   simpler to access because it does some parsing for you already, the actual source of truth remains `scope` - not the
   request. If you need to modify the data of the request you must modify the scope dictionary, not any ephemeral
   request objects created as in the above.
2. Once the middleware finishes doing whatever its doing, it should pass `scope`, `receive` and `send` to
   either `self.app` or an instance of `Response` - this is equivalent in other middleware architectures to
   calling `next`, which is what happens in the last line of the example.

### Modifying Responses using the MiddlewareProtocol

While Starlite exposes a special life-cycle hook called [After Request](13-lifecycle-hooks.md#After Request),
which is in most cases the correct place to modify a response. Sometimes its desirable to do this using middleware. To
do this, you will need to wrap the `send` function, for example:

```python
import time

from starlette.datastructures import MutableHeaders
from starlette.types import Message, Receive, Scope, Send
from starlite import MiddlewareProtocol
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

## Built-in Middlewares

Starlette includes several builtin middlewares - you can see the list in the Starlette docs. Of these middlewares,
Starlite offers a simple way to use two of them:

### CORS

CORS ([Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)) is a common security
mechanism - that is often implemented using middleware. To enable CORS in a starlite application simply pass an instance
of `starlite.config.CORSConfig` to the Starlite constructor:

```python
from starlite import CORSConfig, Starlite

cors_config = CORSConfig(allow_origins=["https://www.example.com"])

app = Starlite(route_handlers=[...], cors_config=cors_config)
```

You can pass the following kwargs to CORSConfig:

- `allow_origins`: list of domain schemas, defaults to `["*"]`
- `allow_methods`: list of http methods, defaults to `["*"]`
- `allow_headers`: list of header keys, defaults to `["*"]`
- `allow_credentials`: A boolean dictating whether CORS should support cookies in cross-origin requests. Defaults
  to `False`.
- `allow_origin_regex`: A regex string that is matches against incoming request origins. Defaults to `None`.
- `expose_headers`: A list of response headers to expose. Defaults to `[]`.
- `max_age`: Sets a response header instructing the max amount of _seconds_ that the browser should cache a CORS
  response. Defaults to 600.

<!-- prettier-ignore -->
!!! note The asterisks symbol in the above kwargs means "match any".

You can read more about this middleware in the [starlette docs](https://www.starlette.io/middleware/#corsmiddleware).

### Trusted Hosts

Another common security mechanism is to require that each incoming request has a "HOST" header, and then to restrict
hosts to a specific set of domains - what's called "allowed hosts". To enable this middleware simply pass a list of
trusted hosts to the Starlite constructor:

```python
from starlite import Starlite

app = Starlite(
    request_handlers=[...], allowed_hosts=["*.example.com", "www.wikipedia.org"]
)
```

You can use `*` to match any subdomains, as in the above.

### Compression

HTML responses can optionally be compressed. Starlite has built in support for gzip and brotli. Gzip support is provided through the built in Starlette classes, and brotli support can be added by installing the `brotli` extras.

You can enable either backend by passing an instance of `starlite.config.CompressionConfig` into the `compression_config` application parameter.

#### GZIP

You can enable gzip compression of responses by passing an instance of `starlite.config.GZIPConfig`:

```python
from starlite import Starlite, CompressionConfig

app = Starlite(
    request_handlers=[...], compression_config=CompressionConfig(backend="gzip")
)
```

You can configure two values:

- `minimum_size`: the minimum threshold for response size to enable compression. Smaller responses will not be compressed. Defaults is `500`, i.e. half a kilobyte.
- `gzip_compress_level`: a range between 0-9, see the [official python docs](https://docs.python.org/3/library/gzip.html). Defaults to `9`, which is the maximum value.

#### Brotli

The Brotli package is required to run this middleware. It is available as an extras to starlite with the `brotli` group. (`pip install starlite[brotli]`)

You can enable brotli compression of responses by passing an instance of `starlite.config.BrotliConfig`:

```python
from starlite import Starlite
from starlite.config import CompressionConfig

app = Starlite(
    request_handlers=[...], compression_config=CompressionConfig(backend="brotli")
)
```

You can configure two values:

- `brotli_quality`: the minimum threshold for response size to enable compression. Smaller responses will not be compressed. Defaults is `500`, i.e. half a kilobyte.
- `brotli_mode`: The compression mode can be MODE_GENERIC (default), MODE_TEXT (for UTF-8 format text input) or MODE_FONT (for WOFF 2.0).
- `brotli_lgwin`: Base 2 logarithm of size. Range is 10 to 24. Defaults to 22.
- `brotli_lgblock`: Base 2 logarithm of the maximum input block size. Range is 16 to 24. If set to 0, the value will be set based on the quality. Defaults to 0.
- `brotli_gzip_fallback`: a boolean to indicate if gzip should be use if brotli is not supported.

## Layering Middleware

Starlite following its layered architecture also in middleware - allowing users to define middleware on all layers of
the application - the Starlite instance, routers, controllers and individual route handlers. For example:

```python
from starlite import Starlite, Controller, Router, MiddlewareProtocol, get


class TopLayerMiddleware(MiddlewareProtocol):
    ...


class RouterLayerMiddleware(MiddlewareProtocol):
    ...


class ControllerLayerMiddleware(MiddlewareProtocol):
    ...


class RouteHandlerLayerMiddleware(MiddlewareProtocol):
    ...


class MyController(Controller):
    path = "/controller"
    middleware = [ControllerLayerMiddleware]

    @get("/handler", middleware=[RouteHandlerLayerMiddleware])
    def my_route_handlers(self) -> dict[str, str]:
        return {"hello": "world"}


router = Router(path="/router", middleware=[RouterLayerMiddleware])

app = Starlite(route_handlers=[router], middleware=[TopLayerMiddleware])
```

In the above example a request to "/router/controller/handler" will be processed by `TopLayerMiddleware`
-> `RouterLayerMiddleware` -> `ControllerLayerMiddleware` -> `RouteHandlerLayerMiddleware`. If multiple middlewares were
declared in a layer, these middlewares would be processed in the order of the list. I.e. in the example
below, `TopLayerMiddleware1` receives the `scope`, `receive` and `send` first, and it either creates a response and
responds, or calls
`TopLayerMiddleware2`:

```python
from starlite import Starlite, MiddlewareProtocol


class TopLayerMiddleware1(MiddlewareProtocol):
    ...


class TopLayerMiddleware2(MiddlewareProtocol):
    ...


app = Starlite(
    route_handlers=[...], middleware=[TopLayerMiddleware1, TopLayerMiddleware2]
)
```

## Middlewares and Exceptions

When an exception is raised by a route handler or dependency and is then transformed into a response by
an [exception handler](17-exceptions#exception-handling), middlewares are still applied to it. The one limitation on
this though are the two exceptions that can be raised by the ASGI router - `404 Not Found` and `405 Method Not Allowed`.
These exceptions are raised before them middleware stack is called, and are only handled by exceptions handlers defined
on the Starlite app instance itself. Thus if you need to modify the responses generated for these exceptions, you will
need to define a custom exception handler on the app instance.
