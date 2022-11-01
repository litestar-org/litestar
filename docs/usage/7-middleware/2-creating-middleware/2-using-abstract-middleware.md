# Inheriting AbstractMiddleware

Starlite offers an `AbstractMiddleware` class that can be extended to create middleware:

```python
from typing import TYPE_CHECKING
from time import time

from starlite import AbstractMiddleware, ScopeType
from starlette.datastructures import MutableHeaders


if TYPE_CHECKING:
    from starlite.types import Message, Receive, Scope, Send


class MyMiddleware(AbstractMiddleware):
    scopes = {ScopeType.HTTP}
    exclude = ["first_path", "second_path"]
    exclude_opt_key = "exclude_from_middleware"

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        start_time = time()

        async def send_wrapper(message: "Message") -> None:
            if message["type"] == "http.response.start":
                process_time = time() - start_time
                headers = MutableHeaders(scope=message)
                headers.append("X-Process-Time", str(process_time))
                await send(message)

        await self.app(scope, receive, send_wrapper)
```

The three class variables defined in the above example `scopes`, `exclude` and `exclude_opt_key` can be used to fine-tune
for which routes and request types the middleware is called:

1. The scopes variable is a set that can include either or both`ScopeType.HTTP` and `ScopeType.WEBSOCKET`, with the default being both.
2. `exclude` accepts either a single string or list of strings that are compiled into a regex against which the request's `path` is checked.
3. `exclude_opt_key` is the key to use for in a route handler's `opt` dict for a boolean, whether to omit from the middleware.

Thus, in the following example, the middleware will only run against the route handler called `not_excluded_handler`:

``` py
--8<-- "examples/middleware/base.py"
```
