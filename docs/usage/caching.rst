Caching
=======

Caching responses
------------------

Sometimes it's desirable to cache some responses, especially if these involve expensive calculations, or when polling is
expected. Litestar comes with a simple mechanism for caching:

.. code-block:: python

   from litestar import get


   @get("/cached-path", cache=True)
   def my_cached_handler() -> str: ...

By setting :paramref:`~litestar.handlers.HTTPRouteHandler.cache` to ``True``, the response from the handler
will be cached. If no ``cache_key_builder`` is set in the route handler, caching for the route handler will be
enabled for the :attr:`~.config.response_cache.ResponseCacheConfig.default_expiration`.

.. note:: If the default :paramref:`~litestar.config.response_cache.ResponseCacheConfig.default_expiration` is set to
    ``None``, setting up the route handler with :paramref:`~litestar.handlers.HTTPRouteHandler.cache` set to ``True``
    will keep the response in cache indefinitely.

Alternatively you can specify the number of seconds to cache the responses from the given handler like so:

.. code-block:: python
    :caption: Caching the response for 120 seconds by setting the :paramref:`~litestar.handlers.HTTPRouteHandler.cache`
      parameter to the number of seconds to cache the response.
    :emphasize-lines: 4

    from litestar import get


    @get("/cached-path", cache=120)  # seconds
    def my_cached_handler() -> str: ...


If you want the response to be cached indefinitely, you can pass the :class:`~.config.response_cache.CACHE_FOREVER`
sentinel instead:

.. code-block:: python
    :caption: Caching the response indefinitely by setting the :paramref:`~litestar.handlers.HTTPRouteHandler.cache`
      parameter to :class:`~litestar.config.response_cache.CACHE_FOREVER`.

    from litestar import get
    from litestar.config.response_cache import CACHE_FOREVER


    @get("/cached-path", cache=CACHE_FOREVER)
    def my_cached_handler() -> str: ...

Configuration
-------------

You can configure caching behaviour on the application level by passing an instance of
:class:`~.config.response_cache.ResponseCacheConfig` to the :class:`Litestar instance <.app.Litestar>`.

Changing where data is stored
+++++++++++++++++++++++++++++

By default, caching will use the :class:`~.stores.memory.MemoryStore`, but it can be configured with
any :class:`~.stores.base.Store`, for example :class:`~.stores.redis.RedisStore`:

.. code-block:: python
    :caption: Using Redis as the cache store.

    from litestar.config.cache import ResponseCacheConfig
    from litestar.stores.redis import RedisStore

    redis_store = RedisStore(url="redis://localhost/", port=6379, db=0)

    cache_config = ResponseCacheConfig(store=redis_store)


Specifying a cache key builder
++++++++++++++++++++++++++++++

Litestar uses the request's path + sorted query parameters as the cache key. This can be adjusted by providing a
"key builder" function, either at application or route handler level.

.. code-block:: python
    :caption: Using a custom cache key builder.

    from litestar import Litestar, Request
    from litestar.config.cache import ResponseCacheConfig


    def key_builder(request: Request) -> str:
        return request.url.path + request.headers.get("my-header", "")


    app = Litestar([], cache_config=ResponseCacheConfig(key_builder=key_builder))

.. code-block:: python
    :caption: Using a custom cache key builder for a specific route handler.

    from litestar import Litestar, Request, get


    def key_builder(request: Request) -> str:
        return request.url.path + request.headers.get("my-header", "")


    @get("/cached-path", cache=True, cache_key_builder=key_builder)
    def cached_handler() -> str: ...
