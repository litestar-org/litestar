Caching
=======

Caching responses
------------------

Sometimes it's desirable to cache some responses, especially if these involve expensive calculations, or when polling is
expected. Litestar comes with a simple mechanism for caching:

.. literalinclude:: /examples/caching/cache.py
    :language: python
    :lines: 1, 4-8

By setting :paramref:`~litestar.handlers.HTTPRouteHandler.cache` to ``True``, the response from the handler
will be cached. If no ``cache_key_builder`` is set in the route handler, caching for the route handler will be
enabled for the :attr:`~.config.response_cache.ResponseCacheConfig.default_expiration`.

The status code, the media type, the body and the headers of the response returned by the handler are cached. The
response is rebuilt from them for every request, so cookies, headers and background tasks configured on the handler or
its layers, ``after_request`` hooks and middleware all run again each time. On cached routes, ``after_request`` hooks
receive the rendered body as ``bytes``. The handler, its dependencies and ``before_request`` hooks are not called when
a response is served from the cache, so an ``after_request`` hook must not depend on state set by them. A background
task attached to the returned :class:`~litestar.response.Response` only runs when the response is not served from the
cache.

Only plain return values, :class:`~litestar.response.Response` and :class:`~litestar.response.Redirect` are cached,
and only if the handler uses the default ``response_class``. Redirects are cached when the
:attr:`~.config.response_cache.ResponseCacheConfig.cache_response_filter` accepts their status code, which by default
is the case for ``301`` and ``308``. A response that sets cookies, other subclasses of
:class:`~litestar.response.Response` (such as :class:`~litestar.response.Stream`, :class:`~litestar.response.File` and
:class:`~litestar.response.Template`), ASGI applications and responses created by exception handlers are not cached.

.. warning:: The default cache key is built from the request method, path and query parameters only, so a cached
    response is served to every user. Do not cache handlers whose response depends on the user, or set a
    ``cache_key_builder`` that includes the user's identity.

Entries are stored under the key returned by the key builder with a ``::body`` suffix, which has to be added when
deleting an entry from the store directly.

.. note:: If the default :paramref:`~litestar.config.response_cache.ResponseCacheConfig.default_expiration` is set to
    ``None``, setting up the route handler with :paramref:`~litestar.handlers.HTTPRouteHandler.cache` set to ``True``
    will keep the response in cache indefinitely.

Alternatively you can specify the number of seconds to cache the responses for the given handler like so:

.. literalinclude:: /examples/caching/cache.py
    :language: python
    :caption: Caching the response for 120 seconds by setting the :paramref:`~litestar.handlers.HTTPRouteHandler.cache`
      parameter to the number of seconds to cache the response.
    :lines: 1, 9-13
    :emphasize-lines: 4

If you want the response to be cached indefinitely, you can pass the :class:`~.config.response_cache.CACHE_FOREVER`
sentinel instead:

.. literalinclude:: /examples/caching/cache.py
    :language: python
    :caption: Caching the response indefinitely by setting the :paramref:`~litestar.handlers.HTTPRouteHandler.cache`
      parameter to :class:`~litestar.config.response_cache.CACHE_FOREVER`.
    :lines: 1-3, 14-18
    :emphasize-lines: 5

Configuration
-------------

You can configure caching behaviour on the application level by passing an instance of
:class:`~.config.response_cache.ResponseCacheConfig` to the :class:`Litestar instance <.app.Litestar>`.

Changing where data is stored
+++++++++++++++++++++++++++++

By default, caching will use the :class:`~.stores.memory.MemoryStore`, but it can be configured with
any :class:`~.stores.base.Store`, for example :class:`~.stores.redis.RedisStore`:

.. literalinclude:: /examples/caching/redis_store.py
    :language: python
    :caption: Using Redis as the cache store.

Specifying a cache key builder
++++++++++++++++++++++++++++++

Litestar uses the request's path + sorted query parameters as the cache key. This can be adjusted by providing a
"key builder" function, either at application or route handler level.

.. literalinclude:: /examples/caching/key_builder.py
    :language: python
    :caption: Using a custom cache key builder.

.. literalinclude:: /examples/caching/key_builder_for_route_handler.py
    :language: python
    :caption: Using a custom cache key builder for a specific route handler.

Using the cache_response_filter
+++++++++++++++++++++++++++++++

The :attr:`~.config.response_cache.ResponseCacheConfig.cache_response_filter` can be customized to implement any caching logic based on the application's needs.
For example, you might want to cache only successful responses, or cache responses based on certain headers or content.

.. literalinclude:: /examples/caching/cache_response_filter.py
    :language: python
    :caption: Using the cache_response_filter to customize caching behavior.

In this example, the `custom_cache_response_filter` function caches only successful (2xx) responses.
