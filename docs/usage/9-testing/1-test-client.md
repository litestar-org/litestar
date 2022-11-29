# Test Client

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

## Using sessions

If you are using [**Session Middleware**](./7-middleware/3-builtin-middlewares/5-session-middleware/) for session persistence
across requests, then you might want to inject or inspect session data outside a request. For this, `TestClient` provides
two methods:

- [set_session_data][starlite.testing.test_client.TestClient.set_session_data]
- [set_session_data][starlite.testing.test_client.TestClient.get_session_data]

!!! important
    - The **Session Middleware** must be enabled in Starlite app provided to the TestClient to use sessions.
    - If you are using the [CookieBackend][starlite.middleware.session.cookie_backend.CookieBackend] you need
      to install the `cryptography` package. You can do so by installing starlite with e.g. `pip install starlite[cryptography]`
      or `poetry install starlite[cryptography]`

```py title="Setting session data"
--8<-- "examples/testing/set_session_data.py"
```

```py title="Getting session data"
--8<-- "examples/testing/get_session_data.py"
```
