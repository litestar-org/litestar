# Response Cookies

Starlite allows you to define response headers by using the `response_cookies` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers and the app
itself:

```python
from starlite import Starlite, Router, Controller, MediaType, get
from starlite.datastructures import Cookie


class MyController(Controller):
    path = "/controller-path"
    response_cookies = [Cookie(key="controller cookie", value="cookie-value")]

    @get(
        path="/",
        response_cookies=[Cookie(key="local cookie", value="cookie-value")],
        media_type=MediaType.TEXT,
    )
    def my_route_handler(self) -> str:
        return "hello world"


router = Router(
    route_handlers=[MyController],
    response_cookies=[Cookie(key="router cookie", value="cookie-value")],
)

app = Starlite(
    route_handlers=[router],
    response_cookies=[Cookie(key="app cookie", value="cookie-value")],
)
```
