:tocdepth: 4

Stores
======

.. py:currentmodule:: starlite.stores


When developing applications, oftentimes a simply storage mechanism is needed, for example when
:doc:`caching response data</lib/usage/caching>` or storing data for
:ref:`server-side sessions <lib/usage/middleware/builtin-middleware:Server-side sessions>`. In cases like these a
traditional database is often not needed, and a simple key/value store suffices.

Starlite provides several low level key value stores, offering an asynchronous interface to store data in a thread-
and process-safe manner. These stores are centrally managed via a
:class:`registry <starlite.stores.registry.StoreRegistry>`, allowing easy access throughout the whole application and
third party integration (for example plugins).


Built-in stores
---------------

:class:`MemoryStore <starlite.stores.memory.MemoryStore>`
    A simple in-memory store, using a dictionary to hold data. This store offers no persistence but is suitable for
    basic applications such as caching and has generally the lowest overhead. This is the default store used by Starlite
    internally.

:class:`FileStore <starlite.stores.file.FileStore>`
    A store that saves data as files on disk. Persistence is built in, and data is easy to extract and back up.
    It is slower compared to in-memory solutions, and primarily suitable for situations when larger amounts of data
    need to be stored, is particularly long-lived, or persistence has a very high importance. Offers `namespacing`_.

:class:`RedisStore <starlite.stores.redis.RedisStore>`
    A store backend by `redis <https://redis.io/>`_. It offers all the guarantees and features of Redis, making it
    suitable for almost all applications. Offers `namespacing`_.

.. admonition:: Why not memcached?
    :class: info

    You might notice that memcached is missing from this list. The reason for this is simply that it's hard to support
    memcached properly, since it's missing a lot of basic functionality like checking a key's expiry time, or something
    like Redis' `SCAN <https://redis.io/commands/scan/>`_ command, which allows to implement pattern-based deletion of
    keys.


Interacting with a store
------------------------

The most fundamental operations of a store are:

- :meth:`get <.base.Store.get>`: To retrieve a stored value
- :meth:`set <.base.Store.set>`: To set a value in the store
- :meth:`delete <.base.Store.delete>`: To delete a stored value


Getting and setting values
++++++++++++++++++++++++++


.. code-block:: python

    from starlite.stores.memory import MemoryStore

    store = MemoryStore()


    async def main() -> None:
        value = await store.get("key")
        print(value)  # this will print 'None', as we have not yet set a value for this key

        await store.set("key", b"value")
        value = await store.get("key")
        print(value)


Setting an expiry time
++++++++++++++++++++++

The :meth:`set <.base.Store.set>` method has an optional parameter ``expires_in``, allowing to specify a time after
which a stored value should expire.


.. code-block:: python

    from asyncio import sleep
    from starlite.stores.memory import MemoryStore

    store = MemoryStore()


    async def main() -> None:
        await store.set("foo", b"bar", expires_in=1)
        value = await store.get("foo")
        print(value)

        await sleep(1)
        value = await store.get("foo")  # this will return 'None', since the key has expired
        print(value)


.. note::
    It is up to the individual store to decide how to handle expired values, and implementations may differ. The
    :class:`redis based store <.redis.RedisStore>` for example uses Redis' native expiry mechanism to handle this,
    while the :class:`FileStore <.file.FileStore>` only deletes expired values when they're trying to be accessed,
    or explicitly deleted via the :meth:`delete_expired <.file.FileStore.delete_expired>` method.


It is also possible to extend the expiry time on each access, which is useful for applications such as server side
sessions or LRU caches:

.. code-block:: python

    from asyncio import sleep
    from starlite.stores.memory import MemoryStore

    store = MemoryStore()


    async def main() -> None:
        await store.set("foo", b"bar", expires_in=1)
        await sleep(0.5)

        await store.get(
            "foo", renew_for=1
        )  # this will reset the time to live to one second

        await sleep(1)
        # it has now been 1.5 seconds since the key was set with a life time of one second,
        # so it should have expired however, since it was renewed for one second, it is still available
        value = await store.get("foo")
        print(value)


Deleting expired values
#######################

When using a :class:`MemoryStore <.memory.MemoryStore>` or :class:`FileStore <.file.FileStore>`, expired data won't be
deleted automatically. Instead, it will only happen when the data is being accessed, or if this process is invoked
explicitly via :meth:`MemoryStore.delete_expired <.memory.MemoryStore.delete_expired>` or
:meth:`FileStore.delete_expired <.file.FileStore.delete_expired>` respectively.

It's a good practice to call ``delete_expired`` periodically, to ensure the size of the stored values does not grow
indefinitely.

In this example, an :ref:`after_response <after_response>` handler is used to delete expired items at most every 30
second:

.. code-block:: python

    from datetime import datetime, timedelta

    from starlite import Starlite, Request
    from starlite.stores.memory import MemoryStore

    memory_store = MemoryStore()


    async def after_response(request: Request) -> None:
        now = datetime.utcnow()
        last_cleared = request.app.state.get("store_last_cleared", now)
        if datetime.utcnow() - last_cleared > timedelta(seconds=30):
            await memory_store.delete_expired()
            app.state["store_last_cleared"] = now


    app = Starlite([], after_response=after_response)


When using the :class:`FileStore <.file.FileStore>`, deleting expired items on startup is also an option:

.. code-block:: python

    from pathlib import Path

    from starlite import Starlite
    from starlite.stores.file import FileStore

    file_store = FileStore(Path("data"))


    async def on_startup() -> None:
        await file_store.delete_expired()


    app = Starlite([], on_startup=[on_startup])


.. note::
    For the :class:`MemoryStore <.memory.MemoryStore>`, this is not needed as the data is simply stored in a dictionary.
    This means that every time a new instance of this store is created, it will start out empty.


What can be stored
++++++++++++++++++

Stores generally operate on :class:`bytes`; They accept bytes to store, and will return bytes. For convenience, the
:meth:`set <.base.Store.set>` method also allows to pass in strings, which will be UTF-8 encoded before being stored.
This means that :meth:`get <.base.Store.get>` will return bytes even when a string has been passed to
:meth:`set <.base.Store.set>`.

The reason for this limitation is simple: Different backends used to store the data offer vastly different encoding,
storage and (de)serialization capacities. Since stores are designed to be interchangeable, this means settling for a
common denominator, a type that all backends will support. :class:`bytes` meet these requirements and make it possible
to store a very wide variety of data.

.. admonition:: Technical details

    :class:`MemoryStore <.memory.MemoryStore>` differs from this, because it does not do any encoding before storing
    the value. This means that it's technically possible to store arbitrary objects in this store, and get the same
    object back. However, this is not reflected in the store's typing, as the underlying :class:`Store <.base.Store>`
    interface does not guarantee this behaviour, and it is not guaranteed that
    :class:`MemoryStore <.memory.MemoryStore>` will always behave in this case.


Namespacing
+++++++++++

When stores are being used for more than one purpose, some extra bookkeeping is required to safely perform bulk
operations such as :class:`delete_all <.base.Store.delete_all>`. If for example a
:class:`RedisStore <.redis.RedisStore>` was used, simply issuing a `FLUSHALL <https://redis.io/commands/flushall/>`_
command might have unforeseen consequences.

To help with this, some stores offer namespacing capabilities, allowing to build a simple hierarchy of stores.
These come with the additional :meth:`with_namespace <.base.NamespacedStore.with_namespace>` method, which returns a
new :class:`NamespacedStore <.base.NamespacedStore>` instance. Once a namespaced store is created, operations on it
will only affect itself and its child namespaces.

When using the :class:`RedisStore <.redis.RedisStore>`, this allows to re-use the same underlying
:class:`Redis <redis.asyncio.Redis>` instance and connection, while ensuring isolation.

.. info::
    :class:`RedisStore <.redis.RedisStore>` uses the ``STARLITE`` namespace by default; all keys created by this store,
    will use the ``STARLITE`` prefix when storing data in redis.
    :meth:`RedisStore.delete_all <.redis.RedisStore.delete_all>` is implemented in such a way that it will only delete
    keys matching the current namespace, making it safe and side-effect free.

    This can be turned off by explicitly passing ``namespace=None`` to the store when creating a new instance.





The registry
------------

Stores are configured through the :class:`registry <starlite.stores.registry.StoreRegistry>`, a central object which
provides access to all registered stores as well as default factories. By default, this requires no configuration;
Everything is set up to work out of the box.


.. code-block:: python

    from starlite import Starlite

    app = Starlite(...)
    some_store = app.stores.get("some_store")


In this example, we request a store ``"name"`` from the registry. Since it hasn't been previously configured, the
registry will set up a new store using its default factory, and register it under the requested name. Subsequent calls
to ``get("some_store")`` will then return the same store.

This means that you won't have to worry about side effects when dealing with specifically requested stores; The registry
ensures that the store you request is unique, so you can safely call e.g.
:meth:`delete_all <starlite.stores.base.Store.delete_all>` on an instance, without effecting other stores.

This pattern of course also works the other way around. Using the
:class:`RateLimitMiddleware <starlite.middleware.rate_limit.RateLimitMiddleware>` as an example, we can easily access
its store the same way:

.. code-block:: python

    from starlite import Starlite
    from starlite.middleware.rate_limit import RateLimitConfig

    app = Starlite(..., rate_limit_config=RateLimitConfig(("second", 1)))
    rate_limit_store = app.stores.get("rate_limit")


Configuration
+++++++++++++

You can provide a set of default stores to the application, which will then be made available via the registry:

.. code-block:: python

    from starlite import Starlite
    from starlite.stores.redis import RedisStore

    app = Starlite(..., stores={"redis": RedisStore.with_client()})
    # now you can do app.stores.get("redis") to gain access to this instance


Using this mechanism, we can also control the stores used by various integrations, such as middlewares:

.. code-block:: python

    from pathlib import Path
    from starlite import Starlite
    from starlite.middleware.session.server_side import ServerSideSessionConfig
    from starlite.stores.redis import RedisStore
    from starlite.stores.file import FileStore

    app = Starlite(
        ...,
        stores={
            "sessions": RedisStore.with_client(),
            "request_cache": FileStore(Path("request-cache")),
        },
        middleware=[ServerSideSessionConfig().middleware],
    )


In this example, we set up the registry with stores using the ``sessions`` and ``request_cache`` keys. These are not
magic constants, but instead configuration values that can be changed. Those names just happen to be their default
values. Adjusting those default values allows us to easily re-use stores, without the need for a more complex setup:

.. code-block:: python

    from pathlib import Path
    from starlite import Starlite
    from starlite.middleware.session.server_side import ServerSideSessionConfig
    from starlite.config.response_cache import ResponseCacheConfig
    from starlite.middleware.rate_limit import RateLimitConfig
    from starlite.stores.redis import RedisStore
    from starlite.stores.file import FileStore

    app = Starlite(
        ...,
        stores={"redis": RedisStore.with_client(), "file": FileStore(Path("data"))},
        response_cache_config=ResponseCacheConfig(store="redis"),
        middleware=[
            ServerSideSessionConfig(store="file").middleware,
            RateLimitConfig(rate_limit=("second", 10), store="redis"),
        ],
    )

Now the rate limit middleware and response caching will use the ``redis`` store, while sessions will be store in the
``file`` store.


The default factory
+++++++++++++++++++

The pattern we've seen above is made possible by using the registry's default factory; A callable that gets invoked
every time we request a store that hasn't been registered yet. It's similar to the ``default`` argument to
:meth:`dict.get`.

By default, the default factory is a function that returns a new
:class:`MemoryStore <starlite.stores.memory.MemoryStore>` instance. This behaviour can be changed by supplying a
custom ``default_factory`` method to the registry.

To make use of this, we can pass a registry instance directly to the application:

.. code-block:: python

    from starlite import Starlite
    from starlite.stores.registry import StoreRegistry
    from starlite.stores.memory import MemoryStore

    memory_store = MemoryStore()


    def default_factory(name: str) -> MemoryStore:
        return memory_store


    app = Starlite(..., stores=StoreRegistry(default_factory=default_factory))


Now we have a registry that will return the same :class:`MemoryStore <starlite.stores.memory.MemoryStore>` every time.

When used in conjunction with a :class:`NamespacedStore <starlite.stores.base.NamespacedStore>`, this is a powerful
pattern, allowing the easy creation of a store hierarchy.

.. code-block:: python

    from pathlib import Path

    from starlite import Starlite, get
    from starlite.middleware.rate_limit import RateLimitConfig
    from starlite.middleware.session.server_side import ServerSideSessionConfig
    from starlite.stores.file import FileStore
    from starlite.stores.registry import StoreRegistry

    root_store = FileStore(Path("data"))


    @get(cache=True)
    def cached_handler() -> str:
        # this will use app.stores.get("request_cache")
        return "Hello, world!"


    app = Starlite(
        [cached_handler],
        stores=StoreRegistry(default_factory=root_store.with_namespace),
        middleware=[
            RateLimitConfig(("second", 1)).middleware,
            ServerSideSessionConfig().middleware,
        ],
    )
