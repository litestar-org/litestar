Caching
=======

Caching responses
------------------

Sometimes it's desirable to cache some responses, especially if these involve expensive calculations, or when polling is
expected. Litestar comes with a simple mechanism for caching:

.. literalinclude:: /examples/caching/caching_response.py
    :caption: Caching response
    :language: python


By setting ``cache=True`` in the route handler, caching for the route handler will be enabled for the
:attr:`ResponseCacheConfig.default_expiration <.config.response_cache.ResponseCacheConfig.default_expiration>`.


.. note::
    If the default ``default_expiration`` is set to ``None``, setting up the route handler with ``cache=True`` will keep
    the response in cache indefinitely.

Alternatively you can specify the number of seconds to cache the responses from the given handler like so:

.. literalinclude:: /examples/caching/caching_duration.py
    :caption: Caching with specific duration
    :language: python


If you want the response to be cached indefinitely, you can pass the :class:`.config.response_cache.CACHE_FOREVER`
sentinel instead:

.. literalinclude:: /examples/caching/caching_forever.py
    :caption: Caching forever
    :language: python


Configuration
-------------

You can configure caching behaviour on the application level by passing an instance of
:class:`ResponseCacheConfig <.config.response_cache.ResponseCacheConfig>` to the :class:`Litestar instance <.app.Litestar>`.


Changing where data is stored
+++++++++++++++++++++++++++++

By default, caching will use the :class:`MemoryStore <.stores.memory.MemoryStore>`, but it can be configured with
any :class:`Store <.stores.base.Store>`, for example :class:`RedisStore <.stores.redis.RedisStore>`:

.. literalinclude:: /examples/caching/caching_storage_redis.py
    :caption: Caching with redis
    :language: python


Specifying a cache key builder
++++++++++++++++++++++++++++++

Litestar uses the request's path + sorted query parameters as the cache key. This can be adjusted by providing a
"key builder" function, either at application or route handler level.

.. literalinclude:: /examples/caching/caching_key_builder.py
    :caption: Caching key builder
    :language: python


.. literalinclude:: /examples/caching/caching_key_builder_specific_route.py
    :caption: Caching key builder for a specific route
    :language: python
