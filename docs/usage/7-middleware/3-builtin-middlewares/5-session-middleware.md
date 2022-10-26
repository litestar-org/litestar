# Session Middleware

Starlite includes a [SessionMiddleware][starlite.middleware.session.SessionMiddleware],
offering client- and server-side sessions. Different storage mechanisms are available through
[SessionBackends][starlite.middleware.session.base.SessionBackend], and include support for
storing data in:

- [Cookies](#client-side-sessions)
- [Files](#file-storage)
- [Redis](#redis-storage) (through `aioredis`)
- [Memcached](#memcached-storage) (through `aiomcache`)
- [Databases](#database-storage) (through `sqlalchemy`)
- [Memory](#in-memory-storage)

!!! info
    The Starlite's `SesionMiddleware` is not based on the
    [Starlette SessionMiddleware](https://www.starlette.io/middleware/#sessionmiddleware),
    although it is compatible with it, and it can act as a drop-in replacement.

## Setting up the middleware

To start using sessions in your application all you have to do is create an instance
of a [configuration][starlite.middleware.session.base.BaseBackendConfig] object and
add its middleware to your application's middleware stack:

=== "Python > 3.7"

    ```py title="Hello World"
    --8<-- "examples/middleware/session/cookies_full_example_py37.py"
    ```

=== "Python > 3.9"

    ```py title="Hello World"
    --8<-- "examples/middleware/session/cookies_full_example.py"
    ```

!!! note
    Since both client- and server-side sessions rely on cookies (one for storing the actual session
    data, the other for storing the session ID), they share most of the cookie configuration.
    A complete reference of the cookie configuration can be found here:

    [BaseBackendConfig][starlite.middleware.session.base.BaseBackendConfig]

## Client-side sessions

Client side sessions are available through the [CookieBackend][starlite.middleware.session.cookie_backend.CookieBackend],
which offers strong AES-CGM encryption security best practices while support cookie splitting.

!!! important
    `CookieBackend` requires the [cryptography](https://cryptography.io/en/latest/) library,
    which can be installed together with starlite as an extra using `pip install starlite[cryptography]`

```py title="cookie_backend.py"
--8<-- "examples/middleware/session/cookie_backend.py"
```

!!! tip "See also"
    [CookieBackendConfig][starlite.middleware.session.cookie_backend.CookieBackendConfig]

## Server-side sessions

Server side session store data - as the name suggests - on the server instead of the client.
They use a cookie containing a session ID which is a randomly generated string to identify a client
and load the appropriate data from the storage backend.

### File storage

The [FileBackend][starlite.middleware.session.file_backend.FileBackend] will store session data
in files on disk, alongside some metadata. Files containing expired sessions will only be deleted
when trying to access them. Expired session files can be manually deleted using the
[delete_expired][starlite.middleware.session.file_backend.FileBackend.delete_expired] method.

```py title="file_backend.py"
--8<-- "examples/middleware/session/file_backend.py"
```

!!! tip "See also"
    - [Accessing the storage backend directly](#accessing-the-storage-backend-directly)
    - [BaseBackendConfig][starlite.middleware.session.base.BaseBackendConfig]
    - [ServerSideSessionConfig][starlite.middleware.session.base.ServerSideSessionConfig]
    - [FileBackendConfig][starlite.middleware.session.file_backend.FileBackendConfig]

### Redis storage

The [Redis backend][starlite.middleware.session.redis_backend.RedisBackend] can store session data
in redis. Session data stored in redis will expire automatically after its
[max_age][starlite.middleware.session.base.BaseBackendConfig.max_age] has been passed.

!!! important
    This requires the `redis` package. To install it you can install starlite with
    `pip install starlite[redis]`

```py title="redis_backend.py"
--8<-- "examples/middleware/session/redis_backend.py"
```

!!! tip "See also"
    - [Accessing the storage backend directly](#accessing-the-storage-backend-directly)
    - [BaseBackendConfig][starlite.middleware.session.base.BaseBackendConfig]
    - [ServerSideSessionConfig][starlite.middleware.session.base.ServerSideSessionConfig]

### Memcached storage

The [Memcached backend][starlite.middleware.session.memcached_backend.MemcachedBackend] can store session data
in memcached. Session data stored in memcached will expire automatically after its
[max_age][starlite.middleware.session.base.BaseBackendConfig.max_age] has been passed.

!!! important
    This requires the `aiomamcache` package. To install it you can install starlite with
    `pip install starlite[memcached]`

```py title="memcached_backend.py"
--8<-- "examples/middleware/session/memcached_backend.py"
```

!!! tip "See also"
    - [Accessing the storage backend directly](#accessing-the-storage-backend-directly)
    - [BaseBackendConfig][starlite.middleware.session.base.BaseBackendConfig]
    - [ServerSideSessionConfig][starlite.middleware.session.base.ServerSideSessionConfig]

### In-memory storage

The [Memory backend][starlite.middleware.session.memory_backend.MemoryBackend] can store
session data in memory.

!!! Danger
    This should not be used in production. It primarily exists as a dummy backend for
    testing purposes. It is not thread or process safe, and data will not be persisted.

```py title="memory_backend.py"
--8<-- "examples/middleware/session/memory_backend.py"
```

### Database storage

Database storage is currently offered through the
[SQLAlchemyBackend][starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend].
It supports both sync and async-engines and integrates with the [SQLAlchemyPlugin](/starlite/usage/10-plugins/1-sql-alchemy-plugin).
Expired sessions will only be deleted when trying to access them. They can be manually deleted using the
[delete_expired][starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend.delete_expired] method.

There are two backends for SQLAlchemy:

- [SQLAlchemyBackend][starlite.middleware.session.sqlalchemy_backend.SQLAlchemyBackend] for synchronous engines
- [AsyncSQLAlchemyBackend][starlite.middleware.session.sqlalchemy_backend.AsyncSQLAlchemyBackend] for asynchronous engines

When using the [configuration][starlite.middleware.session.sqlalchemy_backend.SQLAlchemyBackendConfig] object,
it will automatically pick the correct backend to use based on the engine configuration.

!!! info
    This requires [sqlalchemy](https://sqlalchemy.org/). You can install it via
    `pip install sqlalchemy`.

=== "Synchronous engine"

    ```py title="sqlalchemy_backend.py"
    --8<-- "examples/middleware/session/sqlalchemy_backend.py"
    ```

=== "Asynchronous engine"

    ```py title="sqlalchemy_backend.py"
    --8<-- "examples/middleware/session/sqlalchemy_backend_async.py"
    ```

#### Supplying your own session model

If you wish to extend the built-in session model, you can subclass the
[SessionModelMixin][starlite.middleware.session.sqlalchemy_backend.SessionModelMixin]:

```py title="sqlalchemy_backend_custom_model.py"
--8<-- "examples/middleware/session/sqlalchemy_backend_custom_model.py"
```

!!! tip "See also"
    - [BaseBackendConfig][starlite.middleware.session.base.BaseBackendConfig]
    - [ServerSideSessionConfig][starlite.middleware.session.base.ServerSideSessionConfig]

## Accessing the storage backend directly

In some situations you might want to access the storage backend directly, outside a
request. For example to delete a specific session's data, or delete expired sessions
from the database when using the [SQLAlchemyBackend][starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend].

``` py
--8<-- "examples/middleware/session/backend_access_explicit.py"
```
