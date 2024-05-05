Caching
=======

Cache backends
---------------

Starlite includes a builtin :class:`Cache <starlite.cache.Cache>` that offers a uniform interface to interact with different
"Cache Backends". A *Cache Backend* is a class that either implements or fulfills the interface specified by
:class:`CacheBackendProtocol <starlite.cache.CacheBackendProtocol>` to provide cache services.

Builtin cache backends
++++++++++++++++++++++

Starlite comes with the following builtin cache backends:

By default, Starlite uses the :class:`SimpleCacheBackend <starlite.cache.SimpleCacheBackend>`, which stores values
in local memory with the added security of async locks. This is fine for local development, but it's not a good solution
for production environments.

Starlite also ships with two other ready to use cache backends:

Redis
******

:class:`RedisCacheBackend <starlite.cache.redis_cache_backend.RedisCacheBackend>`, which uses
`Redis <https://github.com/redis/redis-py>`_ as the caching database. Under the hood it uses
`redis-py asyncio <https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html>`_ to make sure requests are
not blocked and `hiredis <https://github.com/redis/hiredis>`_ to boost performance.

.. note::

    ``redis`` is a required dependency when using this backend. You can install it as an extra with
    ``pip install starlite[redis]`` or independently.

Memcached
*********

:class:`MemcachedCacheBackend <starlite.cache.memcached_cache_backend.MemcachedCacheBackend>`, which uses
`memcached <https://memcached.org/>`_ as the caching database. Under the hood it uses
`aiomcache <https://github.com/aio-libs/aiomcache>`_ to make sure requests are not blocked.

.. note::

    ``aiomcache`` is a required dependency when using this backend. You can install it as an extra with
    ``pip install starlite[memcached]`` or independently.


Configuring caching
+++++++++++++++++++

You can configure caching behaviour on the application level by passing an instance of
:class:`CacheConfig <.config.CacheConfig>` to the :class:`Starlite instance <starlite.app.Starlite>`.

Here is an example of how to configure a cache backend

.. tab-set::

    .. tab-item:: Redis
        :sync: redis

        .. code-block:: python

           from starlite import CacheConfig
           from starlite.cache.redis_cache_backend import (
               RedisCacheBackendConfig,
               RedisCacheBackend,
           )

           config = RedisCacheBackendConfig(url="redis://localhost/", port=6379, db=0)
           redis_backend = RedisCacheBackend(config=config)

           cache_config = CacheConfig(backend=redis_backend)

    .. tab-item:: Memcached
        :sync: memcached

        .. code-block:: python

           from starlite import CacheConfig
           from starlite.cache.memcached_cache_backend import (
               MemcachedCacheBackendConfig,
               MemcachedCacheBackend,
           )

           config = MemcachedCacheBackendConfig(url="127.0.0.1", port=11211)
           memcached_backend = MemcachedCacheBackend(config=config)

           cache_config = CacheConfig(backend=memcached_backend)


Creating a custom cache backend
++++++++++++++++++++++++++++++++

Since Starlite relies on the :class:`CacheBackendProtocol <starlite.cache.CacheBackendProtocol>` to define cache,
creating a custom cache backend is very simple - all that is required is to create a class that inherits from the
protocol and implements all its methods, or even a class that simply implements these methods without inheriting from
the protocol. Once this is done, you can use the backend in the cache config.


Response caching
----------------

Sometimes it's desirable to cache some responses, especially if these involve expensive calculations, or when polling is
expected. Starlite comes with a simple mechanism for caching:

.. code-block:: python

   from starlite import get


   @get("/cached-path", cache=True)
   def my_cached_handler() -> str: ...

By setting ``cache=True`` in the route handler, caching for the route handler will be enabled for the default duration,
which is 60 seconds unless modified.

Alternatively you can specify the number of seconds to cache the responses from the given handler like so:

.. code-block:: python

   from starlite import get


   @get("/cached-path", cache=120)  # seconds
   def my_cached_handler() -> str: ...


Specifying a cache key builder
++++++++++++++++++++++++++++++

Starlite uses the request's path + sorted query parameters as the cache key. You can provide a "Key Builder" function to
the route handler if you want to generate different cache keys:

.. code-block:: python

   from starlite import Request, get


   def my_custom_key_builder(request: Request) -> str:
       return request.url.path + request.headers.get("my-header", "")


   @get("/cached-path", cache=True, cache_key_builder=my_custom_key_builder)
   def my_cached_handler() -> str: ...

You can also specify the default cache key builder to use for the entire application (see below).



Interacting with the cache
--------------------------

The Starlite app's cache is exposed as :attr:`cache <.app.Starlite.cache>`, which makes it accessible via the ``scope``
object. For example, you can access the cache in a custom middleware thus:

.. code-block:: python

   from starlite import MiddlewareProtocol
   from starlite.types import Scope, Receive, Send, ASGIApp


   class MyMiddleware(MiddlewareProtocol):
       def __init__(self, app: ASGIApp):
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           cached_value = await scope["app"].cache.get("my-key")
           if cached_value:
               ...

The cache is also exposed as a property on the :class:`ASGIConnection <starlite.connection.ASGIConnection>` and the
:class:`Request <starlite.connection.Request>` and :class:`WebSocket <starlite.connection.WebSocket>` classes that
inherit from it. You can thus interact with the cache inside a route handler easily, for example by doing this:

.. code-block:: python

   from starlite import Request, get


   @get("/")
   async def my_handler(request: Request) -> None:
       cached_value = await request.cache.get("my-key")
       if cached_value:
           ...

.. attention::

   Cache based operations are async because async locking is used to protect against race conditions. If you need to use
   caching - use an async route handler.
