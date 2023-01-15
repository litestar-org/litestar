# Async Testing

If you like async, Starlite also has an async test client built on top of [httpx](https://github.com/encode/httpx). To use the async test client, similarly to the test client,you should pass to it an
instance of Starlite as the `app` kwarg.

Let's use the health check endpoint we used previously:

```python title="my_app/main.py"
from starlite import Starlite, MediaType, get


@get(path="/health-check", media_type=MediaType.TEXT)
def health_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[health_check])
```

And then to test it using the async test client we would do like so:

```python title="tests/test_health_check.py"
from starlite.status_codes import HTTP_200_OK
from starlite.testing import AsyncTestClient

from my_app.main import app


def test_health_check():
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
```

To use the client in multiple places, it's better to make it into a pytest fixture:

```python title="tests/conftest.py"
import pytest

from starlite.testing import AsyncTestClient

from my_app.main import app


@pytest.fixture(scope="function")
def test_client() -> AsyncTestClient:
    return AsyncTestClient(app=app)
```

Then to rewrite the test with our new fixture we would do something like so:

```python title="tests/test_health_check.py"
from starlite.status_codes import HTTP_200_OK
from starlite.testing import AsyncTestClient


def test_health_check(test_client: AsyncTestClient):
    async with test_client as client:
        response = await client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
```

## Using sessions

If you are using [**Session Middleware**](./7-middleware/3-builtin-middlewares/5-session-middleware/) for session persistence
across requests, then you might want to inject or inspect session data outside a request. For this, `AsyncTestClient` provides
two methods:

- [set_session_data][starlite.testing.client.async_client.AsyncTestClient.set_session_data]
- [get_session_data][starlite.testing.client.async_client.AsyncTestClient.get_session_data]

!!! important
    - The **Session Middleware** must be enabled in Starlite app provided to the AsyncTestClient to use sessions.
    - If you are using the [CookieBackend][starlite.middleware.session.cookie_backend.CookieBackend] you need
      to install the `cryptography` package. You can do so by installing starlite with e.g. `pip install starlite[cryptography]`
      or `poetry install starlite[cryptography]`

```py title="Setting session data"
--8<-- "examples/testing/async/set_session_data.py"
```

```py title="Getting session data"
--8<-- "examples/testing/async/get_session_data.py"
```
