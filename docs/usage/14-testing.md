# Testing

Testing is a first class citizen in Starlite, which offers several powerful testing utilities out of the box.

!!! important
    Testing utils rely on extra dependencies. So make sure to install them, e.g.:
    `pip install starlite[testing]` or `poetry install starlite --extras testing`

## Test Client

Starlite extends the Starlette testing client, which in turn is built using
the [httpx](https://github.com/encode/httpx) library. To use the test client you should pass to it an
instance of Starlite as the `app` kwarg.

Let's say we have a very simple app with a health check endpoint:

```python title="my_app/main.py"
from starlite import Starlite, MediaType, get


@get(path="/health-check", media_type=MediaType.TEXT)
def health_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[health_check])
```

We would then test it using the test client like so:

```python title="tests/test_health_check.py"
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient

from my_app.main import app


def test_health_check():
    with TestClient(app=app) as client:
        response = client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
```

Since we would probably need to use the client in multiple places, it's better to make it into a pytest fixture:

```python title="tests/conftest.py"
import pytest

from starlite.testing import TestClient

from my_app.main import app


@pytest.fixture(scope="function")
def test_client() -> TestClient:
    return TestClient(app=app)
```

We would then be able to rewrite our test like so:

```python title="tests/test_health_check.py"
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient


def test_health_check(test_client: TestClient):
    with test_client as client:
        response = client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
```

### Create Session Cookies

If you are using **Session Middleware** for session persistence across requests then your route handlers may expect
preloaded session when mocking the request. To mock request with raw session cookies, you can use
`TestClient.create_session_cookies`. The session middleware will then load the session data from the session
cookies that you provide.

`TestClient.create_session_cookies` accepts the following argument:

- session_data: Dictionary to create raw session cookies from.

To use the same session configuration that you have used in your app for session middleware, import
`SessionCookieConfig` instance from your app.

```python title="tests/test_route_handlers.py"
import pytest
from starlite.testing import TestClient

from my_app.main import app, session_cookie_config_instance


class TestClass:

    @pytest.fixture()
    def test_client(self) -> TestClient:
        with TestClient(app=app, base_url="example.com", session_config=session_cookie_config_instance) as client:
            yield client

    def test_something(self, test_client: TestClient) -> None:
        cookies = test_client.create_session_cookies(session_data={"user": "test_user"})
        # Set raw session cookies to the "cookies" attribute of test_client instance.
        test_client.cookies = cookies
        test_client.get(url="/my_route")
```

#### Set Cookies With Domain

If you have set `domain` in `SessionCookieConfig` instance, the `domain` argument here must take the same parameter. The
domain must follow the format specified in RFC 2109, that is, setting a cookie domain without a preceding dot, like,
*example.com* instead of *.example.com*, is invalid and will not set the cookie.

If you have not set `domain` in `SessionCookieConfig`, the `domain` argument here must match with the domain name in the
`base_url` argument of `TestClient` instance. See the example below.

```python
def test_something(test_client) -> None:
    cookies = test_client.create_session_cookies(session_data={"user": "test_user"})
    # Get domain
    domain = test_client.session.config.domain or test_client.base_url.host
    # Set cookies
    for key, value in cookies.items():
        test_client.cookies.set(key=key, value=value, domain=domain)
    test_client.get(url="/my_route")
```

### Create Session from Raw Cookies

If your route handlers modify data in session, you may want to assert session data to confirm the modification. If you
are using **Session Middleware**, the response from the route handlers will include raw session cookies which are a
serialized image of the session. To assert data in session, `TestClient.get_session_from_cookies` method deserializes
raw session cookies and creates session from them.

```python title="tests/test_route_handlers.py"
import pytest
from starlite.testing import TestClient

from my_app.main import app, session_cookie_config_instance


class TestClass:

    @pytest.fixture()
    def test_client(self) -> TestClient:
        with TestClient(app=app, session_config=session_cookie_config_instance) as client:
            yield client

    def test_something(self, test_client: TestClient) -> None:
        test_client.get(url="/test")
        session = test_client.get_session_from_cookies()
        assert "user" in session
```

!!! important
    The **Session Middleware** must be enabled in Starlite app provided to the TestClient to use sessions.

!!! important
    Use the test client as a context manager (i.e. with the `with`) keyword if you want to use the Starlite app's
    `on_startup` and `on_shutdown`.

## Creating a Test App

Starlite also offers a helper function called `create_test_client` which first creates an instance of Starlite and then
a test client using it. There are multiple use cases for this helper - when you need to check generic logic that is
decoupled from a specific Starlite app, or when you want to test endpoints in isolation.

You can pass to this helper all the kwargs accepted by
the [starlite constructor](0-the-starlite-app/0-the-starlite-app.md), with
the `route_handlers` kwarg being **required**. Yet unlike the Starlite app, which expects `route_handlers` to be a list,
here you can also pass individual values.

For example, you can do this:

```python title="my_app/tests/test_health_check.py"
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client

from my_app.main import health_check


def test_health_check():
    with create_test_client(route_handlers=[health_check]) as client:
        response = client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
```

But also this:

```python title="my_app/tests/test_health_check.py"
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client

from my_app.main import health_check


def test_health_check():
    with create_test_client(route_handlers=health_check) as client:
        response = client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
```

## Using pydantic-factories

Starlite bundles the library [pydantic-factories](https://github.com/Goldziher/pydantic-factories), which offers an easy
and powerful way to generate mock data from pydantic models and dataclasses.

Let's say we have an API that talks to an external service and retrieves some data:

```python title="main.py"
from typing import Protocol, runtime_checkable

from pydantic import BaseModel
from starlite import get


class Item(BaseModel):
    name: str


@runtime_checkable
class Service(Protocol):
    def get(self) -> Item:
        ...


@get(path="/item")
def get_item(service: Service) -> Item:
    return service.get()
```

We could test the `/item` route like so:

```python title="tests/conftest.py"
import pytest

from starlite.status_codes import HTTP_200_OK
from starlite import Provide, create_test_client

from my_app.main import Service, Item, get_item


@pytest.fixture()
def item():
    return Item(name="Chair")


def test_get_item(item: Item):
    class MyService(Service):
        def get_one(self) -> Item:
            return item

    with create_test_client(route_handlers=get_item, dependencies={"service": Provide(lambda: MyService())}) as client:
        response = client.get("/item")
        assert response.status_code == HTTP_200_OK
        assert response.json() == item.dict()
```

While we can define the test data manually, as is done in the above, this can be quite cumbersome. That's
where [pydantic-factories](https://github.com/Goldziher/pydantic-factories) library comes in. It generates mock data for
pydantic models and dataclasses based on type annotations. With it, we could rewrite the above example like so:

```python title="main.py"
from typing import Protocol, runtime_checkable

import pytest
from pydantic import BaseModel
from pydantic_factories import ModelFactory
from starlite.status_codes import HTTP_200_OK
from starlite import Provide, get
from starlite.testing import create_test_client


class Item(BaseModel):
    name: str


@runtime_checkable
class Service(Protocol):
    def get_one(self) -> Item:
        ...


@get(path="/item")
def get_item(service: Service) -> Item:
    return service.get_one()


class ItemFactory(ModelFactory[Item]):
    __model__ = Item


@pytest.fixture()
def item():
    return ItemFactory.build()


def test_get_item(item: Item):
    class MyService(Service):
        def get_one(self) -> Item:
            return item

    with create_test_client(route_handlers=get_item, dependencies={"service": Provide(lambda: MyService())}) as client:
        response = client.get("/item")
        assert response.status_code == HTTP_200_OK
        assert response.json() == item.dict()
```

## Creating a Test Request

Another helper is the `RequestFactory` class, which creates instances of `starlite.connection.Request`.
The use case for this helper is when you need to test logic that expects to receive a request object.

For example, lets say we wanted to unit test a *guard* function in isolation, to which end we'll reuse the examples
from the [guards](9-guards.md) documentation:

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

- `app`: An instance of `starlite.app.Starlite`.
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
- `cookies`: A string representing the cookie header or a list of `starlite.datastructures.Cookie` instances.
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
