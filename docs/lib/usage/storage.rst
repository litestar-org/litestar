Storage
=======

Starlite includes abstractions over common key/value stores, which can be used for
:doc:`/lib/usage/caching`, :ref:`lib/usage/middleware/builtin-middleware:Server-side sessions` or any other purpose
where a simple key value store might be needed.

Currently supported storages are:

- :class:`MemoryStorageBackend <.storage.memory_backend.MemoryStorageBackend>`: A simple in-memory storage
- :class:`FileStorageBackend <starlite.storage.file_backend.FileStorageBackend>`: File-based storage
- :class:`RedisStorageBackend <starlite.storage.redis_backend.RedisStorageBackend>`: Redis based storage

.. admonition:: Why not memcached?
    :class: info

    You might notice that memcached is missing from this list. The reason for this is simply that it's hard to support
    memcached properly, since it's missing a lot of basic functionality like checking a key's expiry time, or something
    like Redis' `SCAN <https://redis.io/commands/scan/>`_ command, which allows to implement pattern-based deletion of
    keys.
