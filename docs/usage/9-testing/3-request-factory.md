# Request Factory

Another helper is the [`RequestFactory`][starlite.testing.RequestFactory] class, which creates instances of
[`starlite.connection.request.Request`][starlite.connection.request.Request]. The use case for this helper is when
you need to test logic that expects to receive a request object.

For example, lets say we wanted to unit test a *guard* function in isolation, to which end we'll reuse the examples
from the [route guards](../8-security/3-guards.md) documentation:

```python title="my_app/guards.py"
from starlite import Request, RouteHandler, NotAuthorizedException


def secret_token_guard(request: Request, route_handler: RouteHandler) -> None:
    if route_handler.opt.get("secret") and not request.headers.get("Secret-Header", "") == route_handler.opt["secret"]:
        raise NotAuthorizedException()
```

We already have our route handler in place:

```python title="my_app/secret.py"
from os import environ

from starlite import get

from my_app.guards import secret_token_guard


@get(path="/secret", guards=[secret_token_guard], opt={"secret": environ.get("SECRET")})
def secret_endpoint() -> None:
    ...
```

We could thus test the guard function like so:

```python title="tests/guards/test_secret_token_guard.py"
import pytest

from starlite import NotAuthorizedException
from starlite.testing import RequestFactory

from my_app.guards import secret_token_guard
from my_app.secret import secret_endpoint


request = RequestFactory().get("/")


def test_secret_token_guard_failure_scenario():
    copied_endpoint_handler = secret_endpoint.copy()
    copied_endpoint_handler.opt["secret"] = None
    with pytest.raises(NotAuthorizedException):
        secret_token_guard(request=request, route_handler=copied_endpoint_handler)


def test_secret_token_guard_success_scenario():
    copied_endpoint_handler = secret_endpoint.copy()
    copied_endpoint_handler.opt["secret"] = "super-secret"
    secret_token_guard(request=request, route_handler=copied_endpoint_handler)
```

The `RequestFactory` constructor accepts the following parameters:

- `app`: An instance of the [`Starlite`][starlite.app.Starlite] class.
- `server`: The server's domain. Defaults to `test.org`.
- `port`: The server's port. Defaults to `3000`.
- `root_path`: Root path for the server. Defaults to `/`.
- `scheme`: Scheme for the server. Defaults to `"http"`.

It exposes methods for all supported HTTP methods:

- `RequestFactory().get()`
- `RequestFactory().post()`
- `RequestFactory().put()`
- `RequestFactory().patch()`
- `RequestFactory().delete()`

All of these methods accept the following parameters:

- `path`: The request's path. This parameter is **required**.
- `headers`: A dictionary of headers. Defaults to `None`.
- `cookies`: A string representing the cookie header or a list of [`Cookie`][starlite.datastructures.Cookie] instances.
  This value can include multiple cookies. Defaults to `None`.
- `session`: A dictionary of session data. Defaults to `None`.
- `user`: A value for `request.scope["user"]`. Defaults to `None`.
- `auth`: A value for `request.scope["auth"]`. Defaults to `None`.
- `state`: Arbitrary request state.
- `path_params`: A string keyed dictionary of path parameter values.
- `http_version`: HTTP version. Defaults to "1.1".
- `route_handler`: A route handler instance or method. If not provided a default handler is set.

In addition, the following methods accepts a few more parameters:

- `RequestFactory().get()`:
- `query_params`: A dictionary of values from which the request's query will be generated.
  Defaults to `None`.
- `RequestFactory().post()`, `RequestFactory().put()`, `RequestFactory().patch()`:
- `request_media_type`: The 'Content-Type' header of the request. Defaults to `None`.
- `data`: A value for the request's body. Can be either a pydantic model instance
  or a string keyed dictionary. Defaults to `None`.
