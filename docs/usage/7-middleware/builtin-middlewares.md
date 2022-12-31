# Built-in middlewares

## CORS

CORS ([Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)) is a common security
mechanism - that is often implemented using middleware. To enable CORS in a starlite application simply pass an instance
of [`CORSConfig`][starlite.config.CORSConfig] to the [Starlite constructor][starlite.app.Starlite]:

```python
from starlite import CORSConfig, Starlite

cors_config = CORSConfig(allow_origins=["https://www.example.com"])

app = Starlite(route_handlers=[...], cors_config=cors_config)
```

See the [API Reference][starlite.config.CORSConfig] for full details on the `CORSConfig` class and the kwargs it accepts.

!!! note
    The asterisks symbol in the above kwargs means "match any".


## Allowed Hosts

Another common security mechanism is to require that each incoming request has a "Host" or "X-Forwarded-Host" header,
and then to restrict hosts to a specific set of domains - what's called "allowed hosts".

Starlite includes an `AllowedHostsMiddleware` class that can be easily enabled by either passing an instance of
[AllowedHostsConfig][starlite.config.AllowedHostsConfig] or a list of domains to
the [Starlite constructor][starlite.app.Starlite]:

```python
from starlite import Starlite, AllowedHostsConfig

app = Starlite(
    route_handlers=[...],
    allowed_hosts=AllowedHostsConfig(
        allowed_hosts=["*.example.com", "www.wikipedia.org"]
    ),
)
```

!!! note
    You can use wildcard prefixes (`*.`) in the beginning of a domain to match any combination of subdomains. Thus,
    `*.example.com` will match `www.example.com` but also `x.y.z.example.com` etc. You can also simply put `*` in trusted
    hosts, which means - allow all. This though is basically turning the middleware off, so it's better to simply not enable
    it to begin with in this case. You should note that a wildcard cannot be used only in the prefix of a domain name,
    not in the middle or end. Doing so will result in a validation exception being raised.

For further configuration options, consult the [config reference documentation][starlite.config.AllowedHostsConfig].


## Compression

HTML responses can optionally be compressed. Starlite has built in support for gzip and brotli. Gzip support is provided through the built-in Starlette classes, and brotli support can be added by installing the `brotli` extras.

You can enable either backend by passing an instance of [`CompressionConfig`][starlite.config.CompressionConfig] into the `compression_config` the [Starlite constructor][starlite.app.Starlite].

### GZIP

You can enable gzip compression of responses by passing an instance of `starlite.config.CompressionConfig` with the `backend` parameter set to `"gzip"`:

You can configure the following additional gzip-specific values:

- `minimum_size`: the minimum threshold for response size to enable compression. Smaller responses will not be compressed. Defaults is `500`, i.e. half a kilobyte.
- `gzip_compress_level`: a range between 0-9, see the [official python docs](https://docs.python.org/3/library/gzip.html). Defaults to `9`, which is the maximum value.

```python
from starlite import Starlite, CompressionConfig

app = Starlite(
    route_handlers=[...],
    compression_config=CompressionConfig(backend="gzip", gzip_compress_level=9),
)
```

### Brotli

The Brotli package is required to run this middleware. It is available as an extras to starlite with the `brotli` extra. (`pip install starlite[brotli]`)

You can enable brotli compression of responses by passing an instance of `starlite.config.CompressionConfig` with the `backend` parameter set to `"brotli"`:

You can configure the following additional brotli-specific values:

- `minimum_size`: the minimum threshold for response size to enable compression. Smaller responses will not be compressed. Defaults is `500`, i.e. half a kilobyte.
- `brotli_quality`: Range [0-11], Controls the compression-speed vs compression-density tradeoff. The higher the quality, the slower the compression.
- `brotli_mode`: The compression mode can be MODE_GENERIC (default), MODE_TEXT (for UTF-8 format text input) or MODE_FONT (for WOFF 2.0).
- `brotli_lgwin`: Base 2 logarithm of size. Range is 10 to 24. Defaults to 22.
- `brotli_lgblock`: Base 2 logarithm of the maximum input block size. Range is 16 to 24. If set to 0, the value will be set based on the quality. Defaults to 0.
- `brotli_gzip_fallback`: a boolean to indicate if gzip should be used if brotli is not supported.

```python
from starlite import Starlite
from starlite.config import CompressionConfig

app = Starlite(
    route_handlers=[...],
    compression_config=CompressionConfig(backend="brotli", brotli_gzip_fallback=True),
)
```


## Rate-Limit Middleware

Starlite includes an optional [`RateLimitMiddleware`][starlite.middleware.rate_limit.RateLimitMiddleware] that follows
the [IETF RateLimit draft specification](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/).

To use the rate limit middleware, use the [`RateLimitConfig`][starlite.middleware.rate_limit.RateLimitConfig]:

``` py
--8<-- "examples/middleware/rate_limit.py"
```

The only required configuration kwarg is `rate_limit`, which expects a tuple containing a time-unit (`second`, `minute`
, `hour`, `day`) and a value for the request quota (integer). For the other configuration options,
[see the additional configuration options in the reference][starlite.middleware.rate_limit.RateLimitConfig].


## Logging Middleware

Starlite ships with a robust logging middleware that allows logging HTTP request and responses while building on
the [app level logging configuration](/starlite/usage/0-the-starlite-app#logging):

```python
from starlite import Starlite, LoggingConfig, get
from starlite.middleware import LoggingMiddlewareConfig

logging_middleware_config = LoggingMiddlewareConfig()


@get("/")
def my_handler() -> dict[str, str]:
    return {"hello": "world"}


app = Starlite(
    route_handlers=[my_handler],
    logging_config=LoggingConfig(),
    middleware=[logging_middleware_config.middleware],
)
```

The logging middleware uses the logger configuration defined on the application level, which allows for using both stdlib
logging or [structlog](https://www.structlog.org/en/stable/index.html), depending on the configuration used (
see [logging](/starlite//usage/0-the-starlite-app.md#logging) for more details).

### Obfuscating Logging Output

Sometimes certain data, e.g. request or response headers, needs to be obfuscated. This is supported by the middleware configuration:

```python
from starlite.middleware import LoggingMiddlewareConfig

logging_middleware_config = LoggingMiddlewareConfig(
    request_cookies_to_obfuscate={"my-custom-session-key"},
    response_cookies_to_obfuscate={"my-custom-session-key"},
    request_headers_to_obfuscate={"my-custom-header"},
    response_headers_to_obfuscate={"my-custom-header"},
)
```

The middleware will obfuscate the headers `Authorization` and `X-API-KEY`, and the cookie `session` by default.

You can read more about the configuration options in the [api reference][starlite.middleware.logging.LoggingMiddlewareConfig]

### Compression and Logging of Response Body

If both [`CompressionConfig`][starlite.config.compression.CompressionConfig] and
[`LoggingMiddleware`][starlite.middleware.logging.LoggingMiddleware] have been defined for the application, the response
body will be omitted from response logging if it has been compressed, even if `"body"` has been included in
[`response_log_fields`][starlite.middleware.logging.LoggingMiddlewareConfig.response_log_fields]. To force the body of
compressed responses to be logged, set
[`include_compressed_body`][starlite.middleware.logging.LoggingMiddlewareConfig.include_compressed_body] to `True`, in
addition to including `"body"` in `response_log_fields`.

## Session Middleware

Starlite includes a [SessionMiddleware][starlite.middleware.session.SessionMiddleware],
offering client- and server-side sessions. Different storage mechanisms are available through
[SessionBackends][starlite.middleware.session.base.BaseSessionBackend], and include support for
storing data in:

- [Cookies](#client-side-sessions)
- [Files](#file-storage)
- [Redis](#redis-storage)
- [Memcached](#memcached-storage) (through `aiomcache`)
- [Databases](#database-storage) (through `sqlalchemy`)
- [Memory](#in-memory-storage)

!!! info
    The Starlite's `SesionMiddleware` is not based on the
    [Starlette SessionMiddleware](https://www.starlette.io/middleware/#sessionmiddleware),
    although it is compatible with it, and it can act as a drop-in replacement.

### Setting up the middleware

To start using sessions in your application all you have to do is create an instance
of a [configuration][starlite.middleware.session.base.BaseBackendConfig] object and
add its middleware to your application's middleware stack:


```py title="Hello World"
--8<-- "examples/middleware/session/cookies_full_example.py"
```

!!! note
    Since both client- and server-side sessions rely on cookies (one for storing the actual session
    data, the other for storing the session ID), they share most of the cookie configuration.
    A complete reference of the cookie configuration can be found here:

    [BaseBackendConfig][starlite.middleware.session.base.BaseBackendConfig]

### Client-side sessions

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

### Server-side sessions

Server side session store data - as the name suggests - on the server instead of the client.
They use a cookie containing a session ID which is a randomly generated string to identify a client
and load the appropriate data from the storage backend.

#### File storage

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

#### Redis storage

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

#### Memcached storage

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

#### In-memory storage

The [Memory backend][starlite.middleware.session.memory_backend.MemoryBackend] can store
session data in memory.

!!! Danger
    This should not be used in production. It primarily exists as a dummy backend for
    testing purposes. It is not process safe, and data will not be persisted.

```py title="memory_backend.py"
--8<-- "examples/middleware/session/memory_backend.py"
```

#### Database storage

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

##### Supplying your own session model

If you wish to extend the built-in session model, you can mixin the
[SessionModelMixin][starlite.middleware.session.sqlalchemy_backend.SessionModelMixin] into your own classes:

```py title="sqlalchemy_backend_custom_model.py"
--8<-- "examples/middleware/session/sqlalchemy_backend_custom_model.py"
```

!!! tip "See also"
    - [BaseBackendConfig][starlite.middleware.session.base.BaseBackendConfig]
    - [ServerSideSessionConfig][starlite.middleware.session.base.ServerSideSessionConfig]

### Accessing the storage backend directly

In some situations you might want to access the storage backend directly, outside a
request. For example to delete a specific session's data, or delete expired sessions
from the database when using the [SQLAlchemyBackend][starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend].

``` py
--8<-- "examples/middleware/session/backend_access_explicit.py"
```
