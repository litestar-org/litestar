Built-in middleware
===================

CORS
----

`CORS (Cross-Origin Resource Sharing) <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_ is a common security
mechanism that is often implemented using middleware. To enable CORS in a starlite application simply pass an instance
of :class:`CORSConfig <starlite.config.CORSConfig>` to the :class:`Starlite constructor <starlite.app.Starlite>`:

.. code-block:: python

   from starlite import CORSConfig, Starlite

   cors_config = CORSConfig(allow_origins=["https://www.example.com"])

   app = Starlite(route_handlers=[...], cors_config=cors_config)


CSRF
----

CSRF (Cross-site request forgery) is a type of attack where unauthorized commands are submitted from a user that the web
application trusts. This attack often uses social engineering that tricks the victim into clicking a URL that contains a
maliciously crafted, unauthorized request for a particular Web application. The user’s browser then sends this
maliciously crafted request to the targeted Web application. If the user is in an active session with the Web application,
the application treats this new request as an authorized request submitted by the user. Thus, the attacker can force the
user to perform an action the user didn't intend, for example:


.. code-block:: text

    POST /send-money HTTP/1.1
    Host: target.web.app
    Content-Type: application/x-www-form-urlencoded

    amount=1000usd&to=attacker@evil.com


This middleware prevents CSRF attacks by doing the following:

1. On the first "safe" request (e.g GET) - set a cookie with a special token created by the server
2. On each subsequent "unsafe" request (e.g POST) - make sure the request contains either a
    form field or an additional header that has this token


To enable CSRF protection in a Starlite application simply pass an instance of
:class:`CSRFConfig <.config.CSRFConfig>` to the Starlite constructor:

.. code-block:: python

    from starlite import Starlite, CSRFConfig

    csrf_config = CSRFConfig(secret="my-secret")

    app = Starlite(route_handlers=[...], csrf_config=csrf_config)


Routes can be marked as being exempt from the protection offered by this middleware via
:ref:`handler opts <handler_opts>`

.. code-block:: python

    from starlite import post


    @post("/post", exclude_from_csrf=True)
    def handler() -> None: ...


If you need to exempt many routes at once you might want to consider using the
:attr:`exclude <.config.CSRFConfig.exclude>` kwarg which accepts list of path
patterns to skip in the middleware.


Allowed Hosts
-------------

Another common security mechanism is to require that each incoming request has a "Host" or "X-Forwarded-Host" header,
and then to restrict hosts to a specific set of domains - what's called "allowed hosts".

Starlite includes an :class:`AllowedHostsMiddleware <.middleware.allowed_hosts.AllowedHostsMiddleware>` class that can be
easily enabled by either passing an instance of :class:`AllowedHostsConfig <starlite.config.AllowedHostsConfig>` or a
list of domains to the :class:`Starlite constructor <starlite.app.Starlite>`:

.. code-block:: python

   from starlite import Starlite, AllowedHostsConfig

   app = Starlite(
       route_handlers=[...],
       allowed_hosts=AllowedHostsConfig(
           allowed_hosts=["*.example.com", "www.wikipedia.org"]
       ),
   )

.. note::

    You can use wildcard prefixes (``*.``) in the beginning of a domain to match any combination of subdomains. Thus,
    ``*.example.com`` will match ``www.example.com`` but also ``x.y.z.example.com`` etc. You can also simply put ``*``
    in trusted hosts, which means allow all. This is akin to turning the middleware off, so in this case it may be
    better to not enable it in the first place. You should note that a wildcard can only be used only in the prefix of a
    domain name, not in the middle or end. Doing so will result in a validation exception being raised.


Compression
-----------

HTML responses can optionally be compressed. Starlite has built in support for gzip and brotli. Gzip support is provided
through the built-in Starlette classes, and brotli support can be added by installing the ``brotli`` extras.

You can enable either backend by passing an instance of :class:`CompressionConfig <starlite.config.CompressionConfig>`
into the ``compression_config`` the :class:`Starlite constructor <starlite.app.Starlite>`.

GZIP
^^^^

You can enable gzip compression of responses by passing an instance of :class:`starlite.config.CompressionConfig` with
the ``backend`` parameter set to ``"gzip"``.

You can configure the following additional gzip-specific values:


* ``minimum_size``: the minimum threshold for response size to enable compression. Smaller responses will not be
    compressed. Defaults is ``500``, i.e. half a kilobyte.
* ``gzip_compress_level``: a range between 0-9, see the `official python docs <https://docs.python.org/3/library/gzip.html>`_.
    Defaults to ``9`` , which is the maximum value.

.. code-block:: python

   from starlite import Starlite, CompressionConfig

   app = Starlite(
       route_handlers=[...],
       compression_config=CompressionConfig(backend="gzip", gzip_compress_level=9),
   )

Brotli
^^^^^^

The Brotli package is required to run this middleware. It is available as an extras to starlite with the ``brotli``
extra (``pip install starlite[brotli]``).

You can enable brotli compression of responses by passing an instance of :class:`starlite.config.CompressionConfig` with
the ``backend`` parameter set to ``"brotli"``.

You can configure the following additional brotli-specific values:


* ``minimum_size``: the minimum threshold for response size to enable compression. Smaller responses will not be
    compressed. Defaults is ``500``, i.e. half a kilobyte.
* ``brotli_quality``: Range [0-11], Controls the compression-speed vs compression-density tradeoff. The higher the
    quality, the slower the compression.
* ``brotli_mode``: The compression mode can be MODE_GENERIC (default), MODE_TEXT (for UTF-8 format text input) or
    MODE_FONT (for WOFF 2.0).
* ``brotli_lgwin``: Base 2 logarithm of size. Range is 10 to 24. Defaults to 22.
* ``brotli_lgblock``: Base 2 logarithm of the maximum input block size. Range is 16 to 24. If set to 0, the value will
    be set based on the quality. Defaults to 0.
* ``brotli_gzip_fallback``: a boolean to indicate if gzip should be used if brotli is not supported.

.. code-block:: python

   from starlite import Starlite
   from starlite.config import CompressionConfig

   app = Starlite(
       route_handlers=[...],
       compression_config=CompressionConfig(backend="brotli", brotli_gzip_fallback=True),
   )

Rate-Limit Middleware
---------------------

Starlite includes an optional :class:`RateLimitMiddleware <starlite.middleware.rate_limit.RateLimitMiddleware>` that follows
the `IETF RateLimit draft specification <https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/>`_.

To use the rate limit middleware, use the :class:`RateLimitConfig <starlite.middleware.rate_limit.RateLimitConfig>`:

.. literalinclude:: /examples/middleware/rate_limit.py
    :language: python

The only required configuration kwarg is ``rate_limit``, which expects a tuple containing a time-unit (``second``,
``minute``, ``hour``, ``day``\ ) and a value for the request quota (integer). For the other configuration options.


Logging Middleware
------------------

Starlite ships with a robust logging middleware that allows logging HTTP request and responses while building on
the :ref:`app level logging configuration <usage/the-starlite-app:logging>`:

.. literalinclude:: /examples/middleware/logging_middleware.py
    :language: python


The logging middleware uses the logger configuration defined on the application level, which allows for using both stdlib
logging or `structlog <https://www.structlog.org/en/stable/index.html>`_ , depending on the configuration used
(see :ref:`app level logging configuration <usage/the-starlite-app:logging>` for more details).

Obfuscating Logging Output
^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes certain data, e.g. request or response headers, needs to be obfuscated. This is supported by the middleware
configuration:

.. code-block:: python

   from starlite.middleware import LoggingMiddlewareConfig

   logging_middleware_config = LoggingMiddlewareConfig(
       request_cookies_to_obfuscate={"my-custom-session-key"},
       response_cookies_to_obfuscate={"my-custom-session-key"},
       request_headers_to_obfuscate={"my-custom-header"},
       response_headers_to_obfuscate={"my-custom-header"},
   )

The middleware will obfuscate the headers ``Authorization`` and ``X-API-KEY`` , and the cookie ``session`` by default.


Compression and Logging of Response Body
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If both :class:`CompressionConfig <starlite.config.compression.CompressionConfig>` and
:class:`LoggingMiddleware <starlite.middleware.logging.LoggingMiddleware>` have been defined for the application, the response
body will be omitted from response logging if it has been compressed, even if ``"body"`` has been included in
:class:`response_log_fields <starlite.middleware.logging.LoggingMiddlewareConfig.response_log_fields>`. To force the body of
compressed responses to be logged, set
:attr:`include_compressed_body <starlite.middleware.logging.LoggingMiddlewareConfig.include_compressed_body>` to ``True`` , in
addition to including ``"body"`` in ``response_log_fields``.

Session Middleware
------------------

Starlite includes a :class:`SessionMiddleware <starlite.middleware.session.SessionMiddleware>`,
offering client- and server-side sessions. Different storage mechanisms are available through
:class:`SessionBackends <starlite.middleware.session.base.BaseSessionBackend>`, and include support for
storing data in:

* `Cookies <client side sessions>`_
* `Files <file storage>`_
* `Redis <redis storage>`_
* `Memcached <memcached storage>`_ (through ``aiomcache``)
* `Databases <database storage>`_ (through ``sqlalchemy``)
* `Memory <in memory storage>`_



Setting up the middleware
^^^^^^^^^^^^^^^^^^^^^^^^^

To start using sessions in your application all you have to do is create an instance
of a :class:`configuration <starlite.middleware.session.base.BaseBackendConfig>` object and
add its middleware to your application's middleware stack:

.. literalinclude:: /examples/middleware/session/cookies_full_example.py
    :caption: Hello World
    :language: python


.. note::

    Since both client- and server-side sessions rely on cookies (one for storing the actual session
    data, the other for storing the session ID), they share most of the cookie configuration.
    A complete reference of the cookie configuration can be found at :class:`BaseBackendConfig <starlite.middleware.session.base.BaseBackendConfig>`.

Client-side sessions
^^^^^^^^^^^^^^^^^^^^

Client side sessions are available through the :class:`CookieBackend <starlite.middleware.session.cookie_backend.CookieBackend>`,
which offers strong AES-CGM encryption security best practices while support cookie splitting.

.. important::

    ``CookieBackend`` requires the `cryptography <https://cryptography.io/en/latest/>`_ library,
    which can be installed together with starlite as an extra using ``pip install starlite[cryptography]``

.. literalinclude:: /examples/middleware/session/cookie_backend.py
    :caption: cookie_backend.py
    :language: python


.. seealso::

    :class:`CookieBackendConfig <starlite.middleware.session.cookie_backend.CookieBackendConfig>`


Server-side sessions
^^^^^^^^^^^^^^^^^^^^

Server side session store data - as the name suggests - on the server instead of the client.
They use a cookie containing a session ID which is a randomly generated string to identify a client
and load the appropriate data from the storage backend.

File storage
~~~~~~~~~~~~

The :class:`FileBackend <starlite.middleware.session.file_backend.FileBackend>` will store session data
in files on disk, alongside some metadata. Files containing expired sessions will only be deleted
when trying to access them. Expired session files can be manually deleted using the
:meth:`delete_expired <starlite.middleware.session.file_backend.FileBackend.delete_expired>` method.

.. literalinclude:: /examples/middleware/session/file_backend.py
    :caption: file_backend.py
    :language: python


.. seealso::

    - `Accessing the storage backend directly`_
    - :class:`BaseBackendConfig <starlite.middleware.session.base.BaseBackendConfig>`
    - :class:`ServerSideSessionConfig <starlite.middleware.session.base.ServerSideSessionConfig>`
    - :class:`FileBackendConfig <starlite.middleware.session.file_backend.FileBackendConfig>`

Redis storage
~~~~~~~~~~~~~

The :class:`Redis backend <starlite.middleware.session.redis_backend.RedisBackend>` can store session data
in redis. Session data stored in redis will expire automatically after its
:attr:`max_age <starlite.middleware.session.base.BaseBackendConfig.max_age>` has been passed.

.. important::

    This requires the ``redis`` package. To install it you can install starlite with
    ``pip install starlite[redis]``

.. literalinclude:: /examples/middleware/session/redis_backend.py
    :caption: redis_backend.py
    :language: python


.. seealso::

    - `Accessing the storage backend directly`_
    - :class:`BaseBackendConfig <starlite.middleware.session.base.BaseBackendConfig>`
    - :class:`ServerSideSessionConfig <starlite.middleware.session.base.ServerSideSessionConfig>`

Memcached storage
~~~~~~~~~~~~~~~~~

The :class:`Memcached backend <starlite.middleware.session.memcached_backend.MemcachedBackend>` can store session data
in memcached. Session data stored in memcached will expire automatically after its
:attr:`max_age <starlite.middleware.session.base.BaseBackendConfig.max_age>` has been passed.

.. important::

    This requires the ``aiomemcache`` package. To install it you can install starlite with
    ``pip install starlite[memcached]``

.. literalinclude:: /examples/middleware/session/memcached_backend.py
    :caption: memcached_backend.py
    :language: python


.. seealso::

    - `Accessing the storage backend directly`_
    - :class:`BaseBackendConfig <starlite.middleware.session.base.BaseBackendConfig>`
    - :class:`ServerSideSessionConfig <starlite.middleware.session.base.ServerSideSessionConfig>`

In-memory storage
~~~~~~~~~~~~~~~~~

The :class:`Memory backend <starlite.middleware.session.memory_backend.MemoryBackend>` can store
session data in memory.

.. important::

    This should not be used in production. It primarily exists as a dummy backend for
    testing purposes. It is not process safe, and data will not be persisted.

.. literalinclude:: /examples/middleware/session/memory_backend.py
    :caption: memory_backend.py
    :language: python


Database storage
~~~~~~~~~~~~~~~~

Database storage is currently offered through the
:class:`SQLAlchemyBackend <starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend>`.
It supports both sync and async-engines and integrates with the
:doc:`SQLAlchemyPlugin </usage/plugins/sqlalchemy>`. Expired sessions will only be deleted when trying to access them.
They can be manually deleted using the
:meth:`delete_expired <starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend.delete_expired>` method.

There are two backends for SQLAlchemy:

* :class:`SQLAlchemyBackend <starlite.middleware.session.sqlalchemy_backend.SQLAlchemyBackend>` for synchronous engines
* :class:`AsyncSQLAlchemyBackend <starlite.middleware.session.sqlalchemy_backend.AsyncSQLAlchemyBackend>` for asynchronous engines

When using the :class:`configuration <starlite.middleware.session.sqlalchemy_backend.SQLAlchemyBackendConfig>` object,
it will automatically pick the correct backend to use based on the engine configuration.

.. important::

    This requires `sqlalchemy <https://sqlalchemy.org/>`_. You can install it via
    ``pip install sqlalchemy``.

.. tab-set::

    .. tab-item:: Synchronous engine

        .. literalinclude:: /examples/middleware/session/sqlalchemy_backend.py
            :caption: sqlalchemy_backend.py
            :language: python



    .. tab-item:: Asynchronous engine

        .. literalinclude:: /examples/middleware/session/sqlalchemy_backend_async.py
            :caption: sqlalchemy_backend.py
            :language: python


Supplying your own session model
""""""""""""""""""""""""""""""""

If you wish to extend the built-in session model, you can mixin the
:class:`SessionModelMixin <starlite.middleware.session.sqlalchemy_backend.SessionModelMixin>` into your own classes:

.. literalinclude:: /examples/middleware/session/sqlalchemy_backend_custom_model.py
    :caption: sqlalchemy_backend_custom_model.py
    :language: python


.. seealso::

    - :class:`BaseBackendConfig <starlite.middleware.session.base.BaseBackendConfig>`
    - :class:`ServerSideSessionConfig <starlite.middleware.session.base.ServerSideSessionConfig>`


Accessing the storage backend directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some situations you might want to access the storage backend directly, outside a
request. For example to delete a specific session's data, or delete expired sessions
from the database when using the :class:`SQLAlchemyBackend <starlite.middleware.session.sqlalchemy_backend.BaseSQLAlchemyBackend>`.

.. literalinclude:: /examples/middleware/session/backend_access_explicit.py
    :language: python
