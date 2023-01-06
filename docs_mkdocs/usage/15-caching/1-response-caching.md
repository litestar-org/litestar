# Response Caching

Sometimes it's desirable to cache some responses, especially if these involve expensive calculations, or when polling is
expected. Starlite comes with a simple mechanism for caching:

```python
from starlite import get


@get("/cached-path", cache=True)
def my_cached_handler() -> str:
    ...
```

By setting `cache=True` in the route handler, caching for the route handler will be enabled for the default duration,
which is 60 seconds unless modified.

Alternatively you can specify the number of seconds to cache the responses from the given handler like so:

```python
from starlite import get


@get("/cached-path", cache=120)  # seconds
def my_cached_handler() -> str:
    ...
```

## Specifying a Cache Key Builder

Starlite uses the request's path + sorted query parameters as the cache key. You can provide a "Key Builder" function to
the route handler if you want to generate different cache keys:

```python
from starlite import Request, get


def my_custom_key_builder(request: Request) -> str:
    return request.url.path + request.headers.get("my-header", "")


@get("/cached-path", cache=True, cache_key_builder=my_custom_key_builder)
def my_cached_handler() -> str:
    ...
```

You can also specify the default cache key builder to use for the entire application (see below).
