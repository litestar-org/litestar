# Creating a Test App

Starlite also offers a helper function called [`create_test_client`][starlite.testing.create_test_client] which first creates
an instance of Starlite and then a test client using it. There are multiple use cases for this helper - when you need to check
generic logic that is decoupled from a specific Starlite app, or when you want to test endpoints in isolation.

You can pass to this helper all the kwargs accepted by
the [starlite constructor](../0-the-starlite-app/0-the-starlite-app.md), with
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
