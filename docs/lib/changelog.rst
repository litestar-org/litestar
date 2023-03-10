:orphan:

2.x Changelog
=============

2.0.0alpha1
-----------

New features
++++++++++++

Validation of controller route handler methods
    Starlite will now validate that no duplicate handlers (that is, they have the same
    path and same method) exist.

    Reference: https://github.com/starlite-api/starlite/pull/1144

HTMX support
    Basic support for HTMX requests and responses.

    Reference: https://github.com/starlite-api/starlite/pull/1086

Alternate constructor ``Starlite.from_config``
    :meth:`Starlite.from_config <starlite.app.Starlite.from_config>` was added to the
    :class:`Starlite <starlite.app.Starlite>` class which allows to construct an instance
    from an :class:`AppConfig <starlite.config.app.AppConfig>` instance.

    Reference: https://github.com/starlite-api/starlite/pull/1190

Web concurrency option for CLI ``run`` command
    A ``--wc`` / --web-concurrency` option was added to the ``starlite run`` command,
    enabling users to specify the amount of worker processes to use. A corresponding
    environment variable ``WEB_CONCURRENCY`` was added as well

    Reference: https://github.com/starlite-api/starlite/pull/1218

Validation of ``state`` parameter in handler functions
    Type annotations of the reserved ``state`` parameter in handler functions will
    now be validated such that annotations using an unsupported type will raise a
    :class:`ImproperlyConfiguredException <starlite.exceptions.ImproperlyConfiguredException>`.

    Reference: https://github.com/starlite-api/starlite/pull/1264

Generic application state
    :class:`ASGIConnection <starlite.connection.base.ASGIConnection>` and its subclasses are now generic on ``State``
    which allow to to fully type hint a request as ``Request[UserType, AuthType, StateType]``.

    Reference: https://github.com/starlite-api/starlite/pull/1030

Dependency injection of classes
    Support using classes (not class instances, which were already supported) as dependency providers.
    With this, now every callable is supported as a dependency provider.

    Reference: https://github.com/starlite-api/starlite/pull/1143

Event bus
    A simple event bus system for Starlite, supporting synchronous and asynchronous listeners and emitters, providing a
    similar interface to handlers. It currently features a simple in-memory, process-local backend. For the future,
    backends that allow inter-process event dispatching are planned.

    Reference: https://github.com/starlite-api/starlite/pull/1105

Unified storage interfaces **[Breaking]**
    Storage backends for server-side sessions and ``Cache <starlite.cache.Cache>`` have been unified and replaced
    by the :doc:`storage module </lib/usage/storage>`, which implements generic asynchronous key/values stores backed
    by memory, the file system or redis.

    .. important::
        This is a breaking change and you need to change your session / cache configuration accordingly

    Reference: https://github.com/starlite-api/starlite/pull/1184


Changes
+++++++

Relaxed type annotations
    Type annotations across the library have been relaxed to more generic forms, for example
    ``Iterable[str]`` instead of ``List[str]`` or ``Mapping[str, str]`` instead of ``Dict[str, str]``.

    Reference: https://github.com/starlite-api/starlite/pull/1140

``type_encoders`` support in ``AbstractSecurityConfig``
    ``type_encoders`` support has been added to
    :class:`AbstractSecurityConfig <starlite.security.base.AbstractSecurityConfig>`, enabling support for customized
    ``type_encoders`` for example in :class:`JWTAuth <starlite.contrib.jwt.jwt_auth.JWTAuth>`.

    Reference: https://github.com/starlite-api/starlite/pull/1167

Renamed handler module names **[Breaking]**
    The modules containing route handlers have been renamed to prevent ambiguity between module and handler names.

    - ``starlite.handlers.asgi`` > ``starlite.handlers.asgi_handlers``
    - ``starlite.handlers.http`` > ``starlite.handlers.http_handlers``
    - ``starlite.handlers.websocket`` > ``starlite.handlers.websocket_handlers``

    Reference: https://github.com/starlite-api/starlite/pull/1170

New plugin protocols **[Breaking]**
    The plugin protocol has been split into three distinct protocols, covering different use cases:

    :class:`InitPluginProtocol <starlite.plugins.InitPluginProtocol>`
        Hook into an application's initialization process

    :class:`SerializationPluginProtocol <starlite.plugins.SerializationPluginProtocol>`
        Extend the serialization and deserialization capabilities of an application

    :class:`OpenAPISchemaPluginProtocol <starlite.plugins.OpenAPISchemaPluginProtocol>`
        Extend OpenAPI schema generation

    Reference: https://github.com/starlite-api/starlite/pull/1176

Unify response headers and cookies **[Breaking]**
    :ref:`lib/usage/responses:Response Headers` and :ref:`lib/usage/responses:Response Cookies` now have the same
    interface, along with the ``headers`` and ``cookies`` keyword arguments to
    :class:`Response <starlite.response.Response>`. They each allow to pass either a
    :class:`Mapping[str, str] <typing.Mapping>`, e.g. a dictionary, or a :class:`Sequence <typing.Sequence>` of
    :class:`ResponseHeaders <starlite.datastructures.response_header.ResponseHeader>` or
    :class:`Cookies <starlite.datastructures.cookie.Cookie>` respectively.

    Reference: https://github.com/starlite-api/starlite/pull/1209

Replace Pydantic models with dataclasses **[Breaking]**
    Several Pydantic models used for configuration have been replaced with dataclasses or plain classes. This change
    should be mostly non-breaking, unless you relied on those configuration objects being Pydantic models. The changed
    models are:


    - :class:`starlite.config.allowed_hosts.AllowedHostsConfig`
    - :class:`starlite.config.app.AppConfig`
    - :class:`starlite.config.cache.CacheConfig`
    - :class:`starlite.config.compression.CompressionConfig`
    - :class:`starlite.config.cors.CORSConfig`
    - :class:`starlite.config.csrf.CSRFConfig`
    - :class:`starlite.logging.config.LoggingConfig`
    - :class:`starlite.openapi.OpenAPIConfig`
    - :class:`starlite.static_files.StaticFilesConfig`
    - :class:`starlite.template.TemplateConfig`
    - :class:`starlite.contrib.jwt.jwt_token.Token`
    - :class:`starlite.contrib.jwt.jwt_auth.JWTAuth`
    - :class:`starlite.contrib.jwt.jwt_auth.JWTCookieAuth`
    - :class:`starlite.contrib.jwt.jwt_auth.OAuth2Login`
    - :class:`starlite.contrib.jwt.jwt_auth.OAuth2PasswordBearerAuth`
    - :class:`starlite.contrib.opentelemetry.OpenTelemetryConfig`
    - :class:`starlite.middleware.logging.LoggingMiddlewareConfig`
    - :class:`starlite.middleware.rate_limit.RateLimitConfig`
    - :class:`starlite.middleware.session.base.BaseBackendConfig`
    - :class:`starlite.middleware.session.client_side.CookieBackendConfig`
    - :class:`starlite.middleware.session.server_side.ServerSideSessionConfig`
    - :class:`starlite.response_containers.ResponseContainer`
    - :class:`starlite.response_containers.File`
    - :class:`starlite.response_containers.Redirect`
    - :class:`starlite.response_containers.Stream`
    - :class:`starlite.security.base.AbstractSecurityConfig`
    - :class:`starlite.security.session_auth.SessionAuth`

    Reference: https://github.com/starlite-api/starlite/pull/1242

SQLAlchemy plugin moved to ``contrib`` **[Breaking]**
    The :class:`SQLAlchemyPlugin` has moved to ``starlite.contrib.sqlalchemy_1.plugin`` and will only be compatible with
    the SQLAlchemy 1.4 release line. The newer SQLAlchemy 2.x releases will be supported by the ``contrib.sqlalchemy``
    module.

    Reference: https://github.com/starlite-api/starlite/pull/1252

Cleanup of the ``starlite`` namespace  **[Breaking]**
    The ``starlite`` namespace has been cleared up, removing many names from it, which now have to be imported from
    their respective submodules individually. This was both done to improve developer experience as well as reduce
    the time it takes to ``import starlite``.
    An overview of the changed import paths can be found in the
    :ref:`migration guide <release-notes/migration_guide_2:Changed module paths>`

    Reference: https://github.com/starlite-api/starlite/issues/1135


Bugfixes
+++++++++

Fix https://github.com/starlite-api/starlite/issues/1256: Resolving of relative paths in ``StaticFilesConfig``
    Using a relative :class:`pathlib.Path` did not resolve correctly and result in a ``NotFoundException``

    Reference: https://github.com/starlite-api/starlite/issues/1256

Fix https://github.com/starlite-api/starlite/issues/1191: ``--reload`` flag to ``starlite run`` not working correctly
    Passing the ``--reload`` flag to the ``starlite run`` command did not work correctly in all circumstances due to an
    issue with uvicorn. This was resolved by invoking uvicorn in a subprocess.

    Reference: https://github.com/starlite-api/starlite/issues/1191

Fix https://github.com/starlite-api/starlite/issues/1210: Optional types generate incorrect OpenAPI schemas
    An optional query parameter was incorrectly represented as

    .. code-block::

        { "oneOf": [
          { "type": null" },
          { "oneOf": [] }
         ]}

    Reference: https://github.com/starlite-api/starlite/issues/1210

Fix https://github.com/starlite-api/starlite/issues/1228: ``LoggingMiddleware`` is sending obfuscated session id to client
    ``LoggingMiddleware`` would in some cases send obfuscated data to the client, due to a bug in the obfuscation function
    which obfuscated values in the input dictionary in-place.

    Reference: https://github.com/starlite-api/starlite/issues/1228

Fix missing ``domain`` configuration value for JWT cookie auth
    :class:`starlite.contrib.jwt.jwt_auth.JWTCookieAuth` didn't set the ``domain`` configuration value on the response
    cookie.

    Reference: https://github.com/starlite-api/starlite/pull/1223/files

Fix https://github.com/starlite-api/starlite/issues/1201: Can not serve static file in ``/`` path
    A validation error made it impossible to serve static files from the root path ``/``.

    Reference: https://github.com/starlite-api/starlite/issues/1201

Fix https://github.com/starlite-api/starlite/issues/1149: Middleware not excluding static path
    A middleware's ``exclude`` parameter would sometimes not be honoured if the path was used to serve static files
    using ``StaticFilesConfig``.

    Reference: https://github.com/starlite-api/starlite/issues/1149
