:orphan:

2.x Changelog
=============

.. changelog:: 2.0.0alpha2

    .. change:: Repository contrib & SQLAlchemy repository
        :type: feature
        :pr: 1254

        Add a a ``repository`` module to ``contrib``, providing abstract base classes
        to implement the repository pattern. Also added was the ``contrib.repository.sqlalchemy``
        module, implementing a SQLAlchemy repository, offering hand-tuned abstractions
        over commonly used tasks, such as handling of object sessions, inserting,
        updating and upserting individual models or collections.

    .. change:: Data stores & registry
        :type: feature
        :pr: 1330
        :breaking:

        The ``starlite.storage`` module added in the previous version has been
        renamed ``starlite.stores`` to reduce ambiguity, and a new feature, the
        :class:`StoreRegistry <.stores.registry.StoreRegistry>` has been introduced;
        It serves as a central place to manage stores and reduces the amount of
        configuration needed for various integrations.

        - Add ``stores`` kwarg to ``Starlite`` and ``AppConfig`` to allow seeding of the ``StoreRegistry``
        - Add ``Starlite.stores`` attribute, containing a ``StoreRegistry``
        - Change ``RateLimitMiddleware`` to use ``app.stores``
        - Change request caching to use ``app.stores``
        - Change server side sessions to use ``app.stores``
        - Move ``starlite.config.cache.CacheConfig`` to  :class:`starlite.config.response_cache.ResponseCacheConfig`
        - Rename ``Starlite.cache_config`` > ``Starlite.response_cache_config``
        - Rename ``AppConfig.cache_config`` > ``response_cache_config``
        - Remove ``starlite/cache`` module
        - Remove ``ASGIConnection.cache`` property
        - Remove ``Starlite.cache`` attribute

        .. attention::
            :class:`RateLimitMiddleware <.middleware.rate_limit.RateLimitMiddleware>`,
            :class:`ResponseCacheConfig <.config.response_cache.ResponseCacheConfig>`,
            and :class:`ServerSideSessionConfig <.middleware.session.server_side.ServerSideSessionConfig>`
            instead of accepting a ``storage`` argument that could be passed a ``Storage`` instance now have to be
            configured via the ``store`` attribute, accepting a string key for the store to be used from the registry.
            The ``store`` attribute has a unique default set, guaranteeing a unique
            :class:`MemoryStore <.stores.memory.MemoryStore>` instance is acquired for every one of them from the
            registry by default

        .. seealso::

            :doc:`/usage/stores`


    .. change:: Add ``starlite.__version__``
        :type: feature
        :pr: 1277

        Add a ``__version__`` constant to the ``starlite`` namespace, containing a
        :class:`NamedTuple <typing.NamedTuple>`, holding information about the currently
        installed version of Starlite


    .. change:: Add ``starlite version`` command to CLI
        :type: feature
        :pr: 1322

        Add a new ``version`` command to the CLI which displays the currently installed
        version of Starlite

        .. seealso::
            :ref:`The version command <usage/cli:version>`


    .. change:: Enhance CLI autodiscovery logic
        :type: feature
        :breaking:
        :pr: 1322

        Update the CLI :ref:`usage/cli:autodiscovery` to only consider canonical modules app and application, but every
        :class:`Starlite <.app.Starlite>` instance or application factory able to return a ``Starlite`` instance within
        those or one of their submodules, giving priority to the canonical names app and application for application
        objects and submodules containing them.

        .. seealso::
            :ref:`CLI autodiscovery <usage/cli:autodiscovery>`

    .. change:: Configurable exception logging and traceback truncation
        :type: feature
        :pr: 1296

        Add three new configuration options to :class:`BaseLoggingConfig <.logging.config.BaseLoggingConfig>`:

        :attr:`log_exceptions <.logging.config.LoggingConfig.log_exceptions>`
            Configure when exceptions are logged.

            ``always``
                Always log exceptions

            ``debug``
                Log exceptions in debug mode only

            ``never``
                Never log exception

        :attr:`traceback_line_limit <.logging.config.LoggingConfig.traceback_line_limit>`
            Configure how many lines of tracback are logged

        :attr:`exception_logging_handler <.logging.config.LoggingConfig.exception_logging_handler>`
            A callable that receives three parameters - the ``app.logger``, the connection scope and the traceback
            list, and should handle logging

        .. seealso::
            :class:`LoggingConfig <.logging.config.LoggingConfig>`


    .. change:: Allow overwriting default OpenAPI response descriptions
        :type: bugfix
        :issue: 1292
        :pr: 1293

        Fix https://github.com/starlite-api/starlite/issues/1292 by allowing to overwrite
        the default OpenAPI response description instead of raising :exc:`ImproperlyConfiguredException`.


    .. change:: Fix regression in path resolution that prevented 404's being raised for false paths
        :type: bugfix
        :pr: 1316
        :breaking:

        Invalid paths within controllers would under specific circumstances not raise a 404. This was a regression
        compared to ``v1.51``

        .. note::
            This has been marked as breaking since one user has reported to rely on this "feature"


    .. change:: Fix ``after_request`` hook not being called on responses returned from handlers
        :type: bugfix
        :pr: 1344
        :issue: 1315

        ``after_request`` hooks were not being called automatically when a :class:`Response <.response.Response>`
        instances was returned from a route handler directly.

        .. seealso::
            :ref:`after_request`


    .. change:: Fix ``SQLAlchemyPlugin`` raises error when using SQLAlchemy UUID
        :type: bugfix
        :pr: 1355

        An error would be raised when using the SQLAlchemy plugin with a
        `sqlalchemy UUID <https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.UUID>`_ type. This
        was fixed by adding it to the provider map.


    .. change:: Fix ``JSON.parse`` error in ReDoc and Swagger OpenAPI handlers
        :type: bugfix
        :pr: 1363ad

        The HTML generated by the ReDoc and Swagger OpenAPI handlers would cause
        `JSON.parse <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/parse>`_
        to throw an error. This was fixed by removing the call to ``JSON.parse``.


    .. change:: Fix CLI prints application info twice
        :type: bugfix
        :pr: 1322

        Fix an error where the CLI would print application info twice on startup


    .. change:: Update ``SimpleEventEmitter`` to use worker pattern
        :type: misc
        :pr: 1346

        :class:`SimpleEventEmitter <.events.emitter.SimpleEventEmitter>` was updated to using an async worker, pulling
        emitted events from a queue and subsequently calling listeners. Previously listeners were called immediately,
        making the operation effectively "blocking".


    .. change:: Make ``BaseEventEmitterBackend.emit`` synchronous
        :type: misc
        :breaking:
        :pr: 1376

        :meth:`BaseEventEmitterBackend.emit <.events.emitter.BaseEventEmitterBackend>`, and subsequently
        :meth:`SimpleEventEmitter.emit <.events.emitter.SimpleEventEmitter>` and
        :meth:`Starlite.emit <.app.Starlite.emit>` have been changed to synchronous function, allowing them to easily be
        used within synchronous route handlers.


    .. change:: Move 3rd party integration plugins to ``contrib``
        :type: misc
        :breaking:
        :pr: Move 3rd party integration plugins to ``contrib``

        - Move ``plugins.piccolo_orm`` > ``contrib.piccolo_orm``
        - Move ``plugins.tortoise_orm`` > ``contrib.tortoise_orm``


    .. change:: Remove ``picologging`` dependency from the ``standard`` package extra
        :type: misc
        :breaking:
        :pr: 1313

        `picologging <https://github.com/microsoft/picologging>`_ has been removed form the ``standard`` package extra.
        If you have been previously relying on this, you need to change ``pip install starlite[standard]`` to
        ``pip install starlite[standard,picologging]``


    .. change:: Replace ``Starlite()`` ``initial_state`` keyword argument with ``state``
        :type: misc
        :pr: 1350
        :breaking:

        The ``initial_state`` argument to :class:`Starlite <.app.Starlite>` has been replaced with a ``state`` keyword
        argument, accepting an optional :class:`State <.datastructures.state.State>` instance.

        Existing code using this keyword argument will need to be changed from

        .. code-block:: python

            from starlite import Starlite

            app = Starlite(..., initial_state={"some": "key"})

        to

        .. code-block:: python

                from starlite import Starlite
                from starlite.datastructures.state import State

                app = Starlite(..., state=State({"some": "key"}))


    .. change:: Remove support for 2 argument form of ``before_send``
        :type: misc
        :pr: 1354
        :breaking:

        ``before_send`` hook handlers initially accepted 2 arguments, but support for a 3 argument form was added
        later on, accepting an additional ``scope`` parameter. Support for the 2 argument form has been dropped with
        this release.

        .. seealso::
            :ref:`before_send`


    .. change:: Standardize module exports
        :type: misc
        :pr: 1273
        :breaking:

        A large refactoring standardising the way submodules make their names available.

        The following public modules have changed their location:

        - ``config.openapi`` > ``openapi.config``
        - ``config.logging`` > ``logging.config``
        - ``config.template`` > ``template.config``
        - ``config.static_files`` > ``static_files.config``

        The following modules have been removed from the public namespace:

        - ``asgi``
        - ``kwargs``
        - ``middleware.utils``
        - ``cli.utils``
        - ``contrib.htmx.utils``
        - ``handlers.utils``
        - ``openapi.constants``
        - ``openapi.enums``
        - ``openapi.datastructures``
        - ``openapi.parameters``
        - ``openapi.path_item``
        - ``openapi.request_body``
        - ``openapi.responses``
        - ``openapi.schema``
        - ``openapi.typescript_converter``
        - ``openapi.utils``
        - ``multipart``
        - ``parsers``
        - ``signature``




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
