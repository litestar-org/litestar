Caching
=======

Response caching
----------------

Sometimes it's desirable to cache some responses, especially if these involve expensive calculations, or when polling is
expected. Starlite comes with a simple mechanism for caching:

.. code-block:: python

   from starlite import get


   @get("/cached-path", cache=True)
   def my_cached_handler() -> str:
       ...

By setting ``cache=True`` in the route handler, caching for the route handler will be enabled for the
:attr:`CacheConfig.default_expiration <.config.cache.CacheConfig.default_expiration>`.

Alternatively you can specify the number of seconds to cache the responses from the given handler like so:

.. code-block:: python

   from starlite import get


   @get("/cached-path", cache=120)  # seconds
   def my_cached_handler() -> str:
       ...


Configuration
-------------

You can configure caching behaviour on the application level by passing an instance of
:class:`CacheConfig <.config.cache.CacheConfig>` to the :class:`Starlite instance <.app.Starlite>`.


Changing where data is stored
+++++++++++++++++++++++++++++

By default, caching will use the :class:`MemoryStorage <.storage.memory.MemoryStorage>`, but it can be configured with
any :class:`Storage <.storage.base.Storage>`, for example :class:`RedisStorage <.storage.redis.RedisStorage>`:

.. code-block:: python

   from starlite.config.cache import CacheConfig
   from starlite.storage.redis import RedisStorage

   redis_storage = RedisStorage(url="redis://localhost/", port=6379, db=0)

   cache_config = CacheConfig(storage=redis_backend)


Specifying a cache key builder
++++++++++++++++++++++++++++++

Starlite uses the request's path + sorted query parameters as the cache key. This can be adjusted by providing a
"key builder" function, either at application or route handler level.

.. code-block:: python

    from starlite import Starlite, Request
    from starlite.config.cache import CacheConfig


    def key_builder(request: Request) -> str:
        return request.url.path + request.headers.get("my-header", "")


    app = Starlite([], cache_config=CacheConfig(key_builder=key_builder))


.. code-block:: python

    from starlite import Starlite, Request, get


    def key_builder(request: Request) -> str:
        return request.url.path + request.headers.get("my-header", "")


    @get("/cached-path", cache=True, cache_key_builder=key_builder)
    def cached_handler() -> str:
        ...
