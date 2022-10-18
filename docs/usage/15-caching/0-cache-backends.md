# Cache Backends

Starlite includes a builtin [Cache][starlite.cache.Cache] that offers a uniform interface to interact with different
"Cache Backends". A __Cache Backend__ is a class that either implements or fulfills the interface specified by
[CacheBackendProtocol][starlite.cache.CacheBackendProtocol] to provide cache services.

## Builtin Cache Backends

Starlite comes with the following builtin cache backends:

By default, Starlite uses the [SimpleCacheBackend][starlite.cache.SimpleCacheBackend], which stores values
in local memory with the added security of async locks. This is fine for local development, but it's not a good solution
for production environments.

Starlite also ships with two other ready to use cache backends:

[`RedisCacheBackend`][starlite.cache.redis_cache_backend.RedisCacheBackend], which uses [Redis](https://github.com/redis/redis-py) as the caching database. Under the hood it uses
  [redis-py asyncio](https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html) to make sure requests are
  not blocked and [hiredis](https://github.com/redis/hiredis) to boost performance.

!!! note
    `redis` is a required dependency when using this backend. You can install it as an extra with
    `pip install starlite[redis]` or independently.

[`MemcachedCacheBackend`][starlite.cache.memcached_cache_backend.MemcachedCacheBackend], which uses
  [memcached](https://memcached.org/) as the caching database. Under the hood it uses
  [aiomcache](https://github.com/aio-libs/aiomcache) to make sure requests are not blocked.

!!! note
  `memcached` is a required dependency when using this backend. You can install it as an extra with
  `pip install starlite[memcached]` or independently.

## Configuring Caching

You can configure caching behaviour on the application level by passing an instance of `CacheConfig` to the Starlite
constructor. See the [API Reference][starlite.config.CacheConfig] for full details on the `CacheConfig` class and the
kwargs it accepts.

Here is an example of how to configure Redis as the cache backend:

```python
from starlite import CacheConfig
from starlite.cache.redis_cache_backend import (
    RedisCacheBackendConfig,
    RedisCacheBackend,
)

config = RedisCacheBackendConfig(url="redis://localhost/", port=6379, db=0)
redis_backend = RedisCacheBackend(config=config)

cache_config = CacheConfig(backend=redis_backend)
```

Or using Memcached:

```python
from starlite import CacheConfig
from starlite.cache.memcached_cache_backend import (
    MemcachedCacheBackendConfig,
    MemcachedCacheBackend,
)

config = MemcachedCacheBackendConfig(url="127.0.0.1", port=11211)
memcached_backend = MemcachedCacheBackend(config=config)

cache_config = CacheConfig(backend=memcached_backend)
```

## Creating a Custom Cache Backend

Since Starlite relies on the [CacheBackendProtocol][starlite.cache.CacheBackendProtocol] to define cache, creating a
custom cache backend is very simple - all that is required is to create a class that inherits from the protocol
and implements all its methods, or even a class that simply implements these methods without inheriting from the protocol.
Once this is done, you can use the backend in the cache config.
