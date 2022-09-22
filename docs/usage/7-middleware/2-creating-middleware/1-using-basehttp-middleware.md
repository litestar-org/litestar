# Using BaseHTTPMiddleware

You can create middleware by subclassing the `starlette.middleware.base.BaseHTTPMiddleware` abstract class:

```python
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class MyRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        logger.info("%s - %s" % request.method, request.url)
        response = await call_next(request)
        return response
```

This class offers an abstraction on top of ASGI - instead of working directly with the ASGI primitives, it offers a
convenient `dispatch` function that offers access to the `Request` object and a `call_next` callback, which is similar
to the interface used by other frameworks (most famously expressJS).

If you want to add kwargs to your middleware, you can of course customize the `__init__` function as well:

```python
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlite.types import ASGIApp

logger = logging.getLogger(__name__)


class MyRequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, my_kwarg: str) -> None:
        super().__init__(app=app)
        self.my_kwarg = my_kwarg

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        logger.info("%s - %s -%s" % self.my_kwarg, request.method, request.url)
        response = await call_next(request)
        return response
```

While using `BaseHTTPMiddleware` as a base is very convenient, it doesn't offer direct access to the ASGI primitives.
Furthermore, Middlewares based on this class do not work `websockets`. Thus, if you want more flexibility and control
you should use the Starlite [MiddlewareProtocol](2-using-middleware-protocol.md).
