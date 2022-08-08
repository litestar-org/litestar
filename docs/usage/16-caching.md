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

## Configuring Caching

You can configure caching behaviour on the application level by passing an instance of `CacheConfig` to the Starlite
constructor. `CacheConfig` accepts 3 optional kwargs:

- `backend`: the cache backend to use. Defaults to an instance of `starlite.cache.SimpleCacheBackend`.
- `expiration`: the default expiration. Defaults to 60 seconds.
- `cache_key_builder`: the default key builder function. As mentioned above, the default key builder uses the
  request.url.path + its sorted query parameters.

### Registering a Cache Backend

Starlite comes with a single builtin cache backend called `SimpleCacheBackend`, which stores values in memory using a
dictionary.

This is fine for local development but is not a production grade solution. In a production environment it's probably a
good idea to use a more robust solution for caching - using a database, disk storage, or an external service such as
[Redis](https://github.com/redis/redis-py), [Memcached](https://pymemcache.readthedocs.io/en/latest/index.html)
or [Etcd](https://pypi.org/project/python-etcd/).

To do this you simply need to either implement the `starlite.cache.CacheBackendProtocol`, or provide an object that
fulfills it. For example, you can directly use all 3 libraries mentioned above without needing to implement anything. To
use Redis as an example:

```python
from redis import Redis
from starlite import CacheConfig

redis = Redis(host="localhost", port=6379, db=0)

cache_config = CacheConfig(backend=redis)
```
