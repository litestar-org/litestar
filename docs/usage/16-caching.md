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
constructor. See the [API Reference][starlite.config.CacheConfig] for full details on the `CacheConfig` class and the
kwargs it accepts.

### Registering a Cache Backend

Starlite comes with the following builtin cache backends:

- `SimpleCacheBackend` which stores values in memory using a dictionary. This is fine for local development
but is not a production grade solution.
- `RedisCacheBackend` uses [Redis](https://github.com/redis/redis-py) as the caching database. Under the hood it uses
[redis-py asyncio](https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html) to make sure requests are
not blocked and [hiredis](https://github.com/redis/hiredis) to boost performance. Please note that Redis is an optional
dependency so in order to use it you need to install Starlite with the `redis_cache_backend` extra, e.g.
`pip install starlite[redis_cache_backend]`. Here is an example of how to configure Redis as the cache backend:

    ```python
    from starlite import CacheConfig
    from starlite.cache import RedisCacheBackendConfig, RedisCacheBackend

    config = RedisCacheBackendConfig(url="redis://localhost/", port=6379, db=0)
    redis_backend = RedisCacheBackend(config=config)

    cache_config = CacheConfig(backend=redis_backend)
    ```

If you're interested in another solution for caching - using a database, disk storage, or an external service such as
[Memcached](https://pymemcache.readthedocs.io/en/latest/index.html)
or [Etcd](https://pypi.org/project/python-etcd/) you need to either implement the
`starlite.cache.CacheBackendProtocol`, or provide an object that fulfills it.
