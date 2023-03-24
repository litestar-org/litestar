:orphan:

2.x Changelog
=============

.. changelog:: 2.0.0alpha1

    .. change:: Validation of controller route handler methods
        :type: feature
        :pr: 1144

        Starlite will now validate that no duplicate handlers (that is, they have the same
        path and same method) exist.

    .. change:: HTMX support
        :type: feature
        :pr: 1086

        Basic support for HTMX requests and responses.

    .. change:: Alternate constructor ``Starlite.from_config``
        :type: feature
        :pr: 1190

        :meth:`Starlite.from_config <starlite.app.Starlite.from_config>` was added to the
        :class:`Starlite <starlite.app.Starlite>` class which allows to construct an instance
        from an :class:`AppConfig <starlite.config.app.AppConfig>` instance.

    .. change:: Web concurrency option for CLI ``run`` command
        :pr: 1218
        :type: feature

        A ``--wc`` / --web-concurrency` option was added to the ``starlite run`` command,
        enabling users to specify the amount of worker processes to use. A corresponding
        environment variable ``WEB_CONCURRENCY`` was added as well

    .. change:: Validation of ``state`` parameter in handler functions
        :type: feature
        :pr: 1264

        Type annotations of the reserved ``state`` parameter in handler functions will
        now be validated such that annotations using an unsupported type will raise a
        :class:`ImproperlyConfiguredException <starlite.exceptions.ImproperlyConfiguredException>`.

    .. change:: Generic application state
        :type: feature
        :pr: 1030

        :class:`ASGIConnection <starlite.connection.base.ASGIConnection>` and its subclasses are now generic on ``State``
        which allow to to fully type hint a request as ``Request[UserType, AuthType, StateType]``.

    .. change:: Dependency injection of classes
        :type: feature
        :pr: 1143

        Support using classes (not class instances, which were already supported) as dependency providers.
        With this, now every callable is supported as a dependency provider.

    .. change:: Event bus
        :pr: 1105
        :type: feature

        A simple event bus system for Starlite, supporting synchronous and asynchronous listeners and emitters, providing a
        similar interface to handlers. It currently features a simple in-memory, process-local backend. For the future,
        backends that allow inter-process event dispatching are planned.

    .. change:: Unified storage interfaces
        :type: feature
        :pr: 1184
        :breaking:

        Storage backends for server-side sessions and ``Cache <starlite.cache.Cache>`` have been unified and replaced
        by the ``starlite.storages``, which implements generic asynchronous key/values stores backed
        by memory, the file system or redis.

        .. important::
            This is a breaking change and you need to change your session / cache configuration accordingly



    .. change:: Relaxed type annotations
        :pr: 1140
        :type: misc

        Type annotations across the library have been relaxed to more generic forms, for example
        ``Iterable[str]`` instead of ``List[str]`` or ``Mapping[str, str]`` instead of ``Dict[str, str]``.

    .. change:: ``type_encoders`` support in ``AbstractSecurityConfig``
        :type: misc
        :pr: 1167

        ``type_encoders`` support has been added to
        :class:`AbstractSecurityConfig <starlite.security.base.AbstractSecurityConfig>`, enabling support for customized
        ``type_encoders`` for example in :class:`JWTAuth <starlite.contrib.jwt.jwt_auth.JWTAuth>`.


    .. change::  Renamed handler module names
        :type: misc
        :breaking:
        :pr: 1170

        The modules containing route handlers have been renamed to prevent ambiguity between module and handler names.

        - ``starlite.handlers.asgi`` > ``starlite.handlers.asgi_handlers``
        - ``starlite.handlers.http`` > ``starlite.handlers.http_handlers``
        - ``starlite.handlers.websocket`` > ``starlite.handlers.websocket_handlers``


    .. change:: New plugin protocols
        :type: misc
        :pr: 1176
        :breaking:

        The plugin protocol has been split into three distinct protocols, covering different use cases:

        :class:`InitPluginProtocol <starlite.plugins.InitPluginProtocol>`
            Hook into an application's initialization process

        :class:`SerializationPluginProtocol <starlite.plugins.SerializationPluginProtocol>`
            Extend the serialization and deserialization capabilities of an application

        :class:`OpenAPISchemaPluginProtocol <starlite.plugins.OpenAPISchemaPluginProtocol>`
            Extend OpenAPI schema generation


    .. change::  Unify response headers and cookies
        :type: misc
        :breaking:
        :pr: 1209

        :ref:`usage/responses:Response Headers` and :ref:`usage/responses:Response Cookies` now have the same
        interface, along with the ``headers`` and ``cookies`` keyword arguments to
        :class:`Response <starlite.response.Response>`. They each allow to pass either a
        :class:`Mapping[str, str] <typing.Mapping>`, e.g. a dictionary, or a :class:`Sequence <typing.Sequence>` of
        :class:`ResponseHeaders <starlite.datastructures.response_header.ResponseHeader>` or
        :class:`Cookies <starlite.datastructures.cookie.Cookie>` respectively.


    .. change:: Replace Pydantic models with dataclasses
        :type: misc
        :breaking:
        :pr: 1242

        Several Pydantic models used for configuration have been replaced with dataclasses or plain classes. This change
        should be mostly non-breaking, unless you relied on those configuration objects being Pydantic models. The changed
        models are:

        - :class:`starlite.config.allowed_hosts.AllowedHostsConfig`
        - :class:`starlite.config.app.AppConfig`
        - :class:`starlite.config.response_cache.ResponseCacheConfig`
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


    .. change:: SQLAlchemy plugin moved to ``contrib``
        :type: misc
        :breaking:
        :pr: 1252

        The :class:`SQLAlchemyPlugin` has moved to ``starlite.contrib.sqlalchemy_1.plugin`` and will only be compatible
        with the SQLAlchemy 1.4 release line. The newer SQLAlchemy 2.x releases will be supported by the
        ``contrib.sqlalchemy`` module.


    .. change:: Cleanup of the ``starlite`` namespace
        :type: misc
        :breaking:
        :pr: 1135

        The ``starlite`` namespace has been cleared up, removing many names from it, which now have to be imported from
        their respective submodules individually. This was both done to improve developer experience as well as reduce
        the time it takes to ``import starlite``.
        An overview of the changed import paths can be found in the
        :ref:`migration guide <release-notes/migration_guide_2:Changed module paths>`

    .. change:: Fix resolving of relative paths in ``StaticFilesConfig``
        :type: bugfix
        :pr: 1256

        Using a relative :class:`pathlib.Path` did not resolve correctly and result in a ``NotFoundException``

    .. change:: Fix ``--reload`` flag to ``starlite run`` not working correctly
        :type: bugfix
        :pr: 1191

        Passing the ``--reload`` flag to the ``starlite run`` command did not work correctly in all circumstances due to an
        issue with uvicorn. This was resolved by invoking uvicorn in a subprocess.


    .. change:: Fix optional types generate incorrect OpenAPI schemas
        :type: bugfix
        :pr: 1210

        An optional query parameter was incorrectly represented as

        .. code-block::

            { "oneOf": [
              { "type": null" },
              { "oneOf": [] }
             ]}


    .. change:: Fix ``LoggingMiddleware`` is sending obfuscated session id to client
        :type: bugfix
        :pr: 1228

        ``LoggingMiddleware`` would in some cases send obfuscated data to the client, due to a bug in the obfuscation
        function which obfuscated values in the input dictionary in-place.


    .. change:: Fix missing ``domain`` configuration value for JWT cookie auth
        :type: bugfix
        :pr: 1223

        :class:`starlite.contrib.jwt.jwt_auth.JWTCookieAuth` didn't set the ``domain`` configuration value on the response
        cookie.


    .. change:: Fix https://github.com/starlite-api/starlite/issues/1201: Can not serve static file in ``/`` path
        :type: bugfix
        :issue: 1201

        A validation error made it impossible to serve static files from the root path ``/`` .

    .. change:: Fix https://github.com/starlite-api/starlite/issues/1149: Middleware not excluding static path
        :type: bugfix
        :issue: 1149

        A middleware's ``exclude`` parameter would sometimes not be honoured if the path was used to serve static files
        using ``StaticFilesConfig``.
