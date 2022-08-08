# Response Cookies

Starlite allows you to define response headers by using the `response_cookies` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers and the app
itself:

```python
from starlite import Starlite, Router, Controller, MediaType, get
from starlite.datastructures import Cookie


class MyController(Controller):
    path = "/controller-path"
    response_cookies = [
        Cookie(
            key="controller-cookie",
            value="controller value",
            description="controller level cookie",
        )
    ]

    @get(
        path="/",
        response_cookies=[
            Cookie(
                key="local-cookie",
                value="local value",
                description="route handler level cookie",
            )
        ],
        media_type=MediaType.TEXT,
    )
    def my_route_handler(self) -> str:
        return "hello world"


router = Router(
    route_handlers=[MyController],
    response_cookies=[
        Cookie(
            key="router-cookie", value="router value", description="router level cookie"
        )
    ],
)

app = Starlite(
    route_handlers=[router],
    response_cookies=[
        Cookie(key="app-cookie", value="app value", description="app level cookie")
    ],
)
```

In the above example, the response returned by `my_route_handler` will have cookies set by each layer of the
application. Cookies are set using
the [Set-Cookie header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie) and with above resulting
in:

```text
Set-Cookie: local-cookie=local value; Path=/; SameSite=lax
Set-Cookie: controller-cookie=controller value; Path=/; SameSite=lax
Set-Cookie: router-cookie=router value; Path=/; SameSite=lax
Set-Cookie: app-cookie=app value; Path=/; SameSite=lax
```

You can easily override cookies declared in higher levels by re-declaring a cookie with the same key in a lower level,
e.g.:

```python
from starlite import Controller, MediaType, get
from starlite.datastructures import Cookie


class MyController(Controller):
    path = "/controller-path"
    response_cookies = [Cookie(key="my-cookie", value="123")]

    @get(
        path="/",
        response_cookies=[Cookie(key="my-cookie", value="456")],
        media_type=MediaType.TEXT,
    )
    def my_route_handler(self) -> str:
        return "hello world"
```

Of the two declarations of `my-cookie` only the route handler one will be used, because its lower level:

```text
Set-Cookie: my-cookie=456; Path=/; SameSite=lax
```

## The Cookie Class

Starlite exports the class `starlite.datastructures.Cookie`. This is a pydantic model that allows you to define the
following kwargs:

- `key`: Key for the cookie. A value for this kwarg is **required**.
- `value`: String value for the cookie. Defaults to `""`.
- `max_age`: Maximal age before the cookie is invalidated. Defaults to `None`.
- `expires`: Expiration date as unix MS timestamp. Defaults to `None`.
- `path`: Path fragment that must exist in the request url for the cookie to be valid. Defaults to `/`.
- `domain`: Domain for which the cookie is valid.
- `secure`: Flag dictating whether https is required for the cookie. Defaults to `False`.
- `httponly`: Forbids javascript to access the cookie via 'Document.cookie'. Defaults to `False`.
- `samesite`: Controls whether a cookie is sent with cross-site requests. Values can be `strict`, `lax` and `none`.
  Defaults to `lax`.
- `description`: Description of the response cookie header for OpenAPI documentation. Defaults to `""`.
- `documentation_only`: Flag dictating whether the Cookie instance is for OpenAPI documentation only. Defaults
  to `False`.

## Dynamic Cookies

While the above scheme works great for static cookie values, it doesn't allow for dynamic cookies. Because cookies are
fundamentally a type of response headers, we can utilize the same strategies we use for
setting [dynamic headers](./4-response-headers.md#dynamic-headers) also here.
