Caching
=======


Configuring caching
-------------------

You can configure caching behaviour on the application level by passing an instance of
:class:`CacheConfig <.config.CacheConfig>` to the :class:`Starlite instance <starlite.app.Starlite>`.

Here is an example of how to configure a cache backend


.. code-block:: python

   from starlite import CacheConfig
   from starlite.cache.redis_cache_backend import (
       RedisCacheBackendConfig,
       RedisCacheBackend,
   )

   config = RedisCacheBackendConfig(url="redis://localhost/", port=6379, db=0)
   redis_backend = RedisCacheBackend(config=config)

   cache_config = CacheConfig(backend=redis_backend)



Response caching
----------------

Sometimes it's desirable to cache some responses, especially if these involve expensive calculations, or when polling is
expected. Starlite comes with a simple mechanism for caching:

.. code-block:: python

   from starlite import get


   @get("/cached-path", cache=True)
   def my_cached_handler() -> str:
       ...

By setting ``cache=True`` in the route handler, caching for the route handler will be enabled for the default duration,
which is 60 seconds unless modified.

Alternatively you can specify the number of seconds to cache the responses from the given handler like so:

.. code-block:: python

   from starlite import get


   @get("/cached-path", cache=120)  # seconds
   def my_cached_handler() -> str:
       ...


Specifying a cache key builder
++++++++++++++++++++++++++++++

Starlite uses the request's path + sorted query parameters as the cache key. You can provide a "Key Builder" function to
the route handler if you want to generate different cache keys:

.. code-block:: python

   from starlite import Request, get


   def my_custom_key_builder(request: Request) -> str:
       return request.url.path + request.headers.get("my-header", "")


   @get("/cached-path", cache=True, cache_key_builder=my_custom_key_builder)
   def my_cached_handler() -> str:
       ...

You can also specify the default cache key builder to use for the entire application (see below).



Interacting with the cache
--------------------------

The Starlite app's cache is exposed as :class:`Starlite.cache <.app.Starlite>`, which makes it accessible via the
``scope`` object. For example, you can access the cache in a custom middleware thus:

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

    Cache based operations are async because async locking is used to protect against race conditions, therefore you
    need to use an async route handler if you want to interact with the cache.
