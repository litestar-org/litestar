:orphan:

2.x Changelog
=============

.. changelog:: 2.0.0alpha5

    .. change:: Pass template context to HTMX template response
        :type: feature
        :pr: 1488

        Pass the template context to the :class:`Template <litestar.response_containers.Template>` returned by
        :class:`htmx.Response <litestar.contrib.htmx.response>`.


    .. change:: OpenAPI support for attrs and msgspec classes
        :type: feature
        :pr: 1487

        Support OpenAPI schema generation for `attrs <https://www.attrs.org>`_ classes and
        `msgspec <https://jcristharif.com/msgspec/>`_ ``Struct``\ s.

    .. change:: SQLAlchemy repository: Add ``ModelProtocol``
        :type: feature
        :pr: 1503

        Add a new class ``contrib.sqlalchemy.base.ModelProtocol``, serving as a generic model base type, allowing to
        specify custom base classes while preserving typing information

    .. change:: SQLAlchemy repository: Support MySQL/MariaDB
        :type: feature
        :pr: 1345

        Add support for MySQL/MariaDB to the SQLAlchemy repository, using the
        `asyncmy <https://github.com/long2ice/asyncmy>`_ driver.

    .. change:: SQLAlchemy repository: Support MySQL/MariaDB
        :type: feature
        :pr: 1345

        Add support for MySQL/MariaDB to the SQLAlchemy repository, using the
        `asyncmy <https://github.com/long2ice/asyncmy>`_ driver.

    .. change:: SQLAlchemy repository: Add matching logic to ``get_or_create``
        :type: feature
        :pr: 1345

        Add a ``match_fields`` argument to
        :meth:`SQLAlchemyAsyncRepository <litestar.contrib.sqlalchemy.repository.SQLAlchemyAsyncRepository.get_or_create>`.
        This lets you lookup a model using a subset of the kwargs you've provided. If the remaining kwargs are different
        from the retrieved model's stored values, an update is performed.

    .. change:: Repository: Extend filter types
        :type: feature
        :pr: 1345

        Add new filters :class:`OrderBy <litestar.contrib.repository.filters.OrderBy>` and
        :class:`SearchFilter <litestar.contrib.repository.filters.SearchFilter>`, providing ``ORDER BY ...`` and
        ``LIKE ...`` / ``ILIKE ...`` clauses respectively

    .. change:: SQLAlchemy repository: Rename ``SQLAlchemyRepository`` > ``SQLAlchemyAsyncRepository``
        :breaking:
        :type: misc
        :pr: 1345

        ``SQLAlchemyRepository`` has been renamed to
        :class:`SQLAlchemyAsyncRepository <litestar.contrib.sqlalchemy.repository.SQLAlchemyAsyncRepository>`.


    .. change:: DTO: Add ``AbstractDTOFactory`` and backends
        :type: feature
        :pr: 1461

        An all-new DTO implementation was added, using ``AbstractDTOFactory`` as a base class, providing Pydantic and
        msgspec backends to facilitate (de)serialization and validation.

    .. change:: DTO: Remove ``from_connection`` / extend ``from_data``
        :breaking:
        :type: misc
        :pr: 1500

        The method ``DTOInterface.from_connection`` has been removed and replaced by ``DTOInterface.from_bytes``, which
        receives both the raw bytes from the connection, and the connection instance. Since ``from_bytes`` now does not
        handle connections anymore, it can also be a synchronous method, improving symmetry with
        ``DTOInterface.from_bytes``.

        The signature of ``from_data`` has been changed to also accept the connection, matching ``from_bytes``'
        signature.

        As a result of these changes,
        :meth:`DTOInterface.from_bytes <litestar.dto.interface.DTOInterface.data_to_encodable_type>` no longer needs to
        receive the connection instance, so the ``request`` parameter has been dropped.

    .. change:: WebSockets: Support DTOs in listeners
        :type: feature
        :pr: 1518

        Support for DTOs has been added to :class:`WebSocketListener <litestar.handlers.WebsocketListener>` and
        :class:`WebSocketListener <litestar.handlers.websocket_listener>`. A ``dto`` and ``return_dto`` parameter has
        been added, providing the same functionality as their route handler counterparts.

    .. change:: DTO based serialization plugin
        :breaking:
        :type: feature
        :pr: 1501

        :class:`SerializationPluginProtocol <litestar.plugins.SerializationPluginProtocol>` has been re-implemented,
        leveraging the new :class:`DTOInterface <litestar.dto.interface.DTOInterface>`.

        If a handler defines a plugin supported type as either the ``data`` kwarg type annotation, or as the return
        annotation for a handler function, and no DTO has otherwise been resolved to handle the type, the protocol
        creates a DTO implementation to represent that type which is then used to de-serialize into, and serialize from
        instances of that supported type.

        .. important::
            The `Piccolo ORM <https://piccolo-orm.com/>`_ and `Tortoise ORM <https://tortoise.github.io/>`_ plugins have
            been removed by this change, but will be re-implemented using the new patterns in a future release leading
            up to the 2.0 release.

    .. change:: SQLAlchemy 1 contrib module removed
        :breaking:
        :type: misc
        :pr: 1501

        As a result of the changes introduced in `#1501 <https://github.com/litestar-org/litestar/pull/1501>`_,
        SQLAlchemy 1 support has been dropped.

        .. note::
            If you rely on SQLAlchemy 1, you can stick to Starlite *1.51* for now. In the future, a SQLAlchemy 1 plugin
            may be released as a standalone package.

    .. change:: Fix inconsistent parsing of unix timestamp between pydantic and cattrs
        :type: bugfix
        :pr: 1492
        :issue: 1491

        Timestamps parsed as :class:`date <datetime.date>` with pydantic return a UTC date, while cattrs implementation
        return a date with the local timezone.

        This was corrected by forcing dates to UTC when being parsed by attrs.

    .. change:: Fix: Retrieve type hints from class with no ``__init__`` method causes error
        :type: bugfix
        :pr: 1505
        :issue: 1504

        An error would occur when using a callable without an :meth:`object.__init__` method was used in a placed that
        would cause it to be inspected (such as a route handler's signature).

        This was caused by trying to access the ``__module__`` attribute of :meth:`object.__init__`, which would fail
        with

        .. code-block::

            'wrapper_descriptor' object has no attribute '__module__'

    .. change:: Fix error raised for partially installed attrs dependencies
        :type: bugfix
        :pr: 1543

        An error was fixed that would cause a :exc:`MissingDependencyException` to be raised when dependencies for
        `attrs <https://www.attrs.org>`_ were partially installed. This was fixed by being more specific about the
        missing dependencies in the error messages.

    .. change:: Change ``MissingDependencyException`` to be a subclass of ``ImportError``
        :type: misc
        :pr: 1557

        :exc:`MissingDependencyException` is now a subclass of :exc:`ImportError`, to make handling cases where both
        of them might be raised easier.

    .. change:: Remove bool coercion in URL parsing
        :breaking:
        :type: bugfix
        :pr: 1550
        :issue: 1547

        When defining a query parameter as ``param: str``, and passing it a string value of ``"true"``, the value
        received by the route handler was the string ``"True"``, having been title cased. The same was true for the value
        of ``"false"``.

        This has been fixed by removing the coercing of boolean-like values during URL parsing and leaving it up to
        the parsing utilities of the receiving side (i.e. the handler's signature model) to handle these values
        according to the associated type annotations.

    .. change:: Update ``standard`` and ``full`` package extras
        :type: misc
        :pr: 1494

        - Add SQLAlchemy, uvicorn, attrs and structlog to the ``full`` extra
        - Add uvicorn to the ``standard`` extra
        - Add ``uvicorn[standard]`` as an optional dependency to be used in the extras

    .. change:: Remove support for declaring DTOs as handler types
        :breaking:
        :type: misc
        :pr: 1534

        Prior to this, a DTO type could be declared implicitly using type annotations. With the addition of the ``dto``
        and ``return_dto`` parameters, this feature has become superfluous and, in the spirit of offering only one clear
        way of doing things, has been removed.

    .. change:: Fix missing ``content-encoding`` headers on gzip/brotli compressed files
        :type: bugfix
        :pr: 1577
        :issue: 1576

        Fixed a bug that would cause static files served via ``StaticFilesConfig`` that have been compressed with gripz
        or brotli to miss the appropriate ``content-encoding`` header.

    .. change:: DTO: Simplify ``DTOConfig``
        :type: misc
        :breaking:
        :pr: 1580

        - The ``include`` parameter has been removed, to provide a more accessible interface and avoid overly complex
          interplay with ``exclude`` and its support for dotted attributes
        - ``field_mapping`` has been renamed to ``rename_fields`` and support to remap field types has been dropped
        - experimental ``field_definitions`` has been removed. It may be replaced with a "ComputedField" in a future
          release that will allow multiple field definitions to be added to the model, and a callable that transforms
          them into a value for a model field. See


.. changelog:: 2.0.0alpha4

    .. change:: ``attrs`` and ``msgspec`` support in :class:`Partial <litestar.partial.Partial>`
        :type: feature
        :pr: 1462

        :class:`Partial <litestar.partial.Partial>` now supports constructing partial models for attrs and msgspec

    .. change:: :class:`Annotated <typing.Annotated>` support for route handler and dependency annotations
        :type: feature
        :pr: 1462

        :class:`Annotated <typing.Annotated>` can now be used in route handler and dependencies to specify additional
        information about the fields.

        .. code-block:: python

            @get("/")
            def index(param: int = Parameter(gt=5)) -> dict[str, int]:
                ...

        .. code-block:: python

            @get("/")
            def index(param: Annotated[int, Parameter(gt=5)]) -> dict[str, int]:
                ...

    .. change:: Support ``text/html`` Media-Type in ``Redirect`` response container
        :type: bugfix
        :issue: 1451
        :pr: 1474

        The media type in :class:`Redirect <litestar.response.RedirectResponse>` won't be forced to ``text/plain`` anymore and
        now supports setting arbitrary media types.


    .. change:: Fix global namespace for type resolution
        :type: bugfix
        :pr: 1477
        :issue: 1472

        Fix a bug where certain annotations would cause a :exc:`NameError`


    .. change:: Add uvicorn to ``cli`` extra
        :type: bugfix
        :issue: 1478
        :pr: 1480

        Add the ``uvicorn`` package to the ``cli`` extra, as it is required unconditionally


    .. change:: Update logging levels when setting ``Litestar.debug`` dynamically
        :type: bugfix
        :issue: 1476
        :pr: 1482

        When passing ``debug=True`` to :class:`Litestar <litestar.app.Litestar>`, the ``litestar`` logger would be set
        up in debug mode, but changing the ``debug`` attribute after the class had been instantiated did not update the
        logger accordingly.

        This lead to a regression where the ``--debug`` flag to the CLI's ``run`` command would no longer have the
        desired affect, as loggers would still be on the ``INFO`` level.


.. changelog:: 2.0.0alpha3

    .. change:: SQLAlchemy 2.0 Plugin
        :type: feature
        :pr: 1395

        A :class:`SQLAlchemyInitPlugin <litestar.contrib.sqlalchemy.plugins.SQLAlchemyInitPlugin>` was added,
        providing support for managed synchronous and asynchronous sessions.

        .. seealso::
            :doc:`/usage/plugins/sqlalchemy/index`

    .. change:: Attrs signature modelling
        :type: feature
        :pr: 1382

        Added support to model route handler signatures with attrs instead of Pydantic

    .. change:: Support setting status codes in ``Redirect`` container
        :type: feature
        :pr: 1412
        :issue: 1371

        Add support for manually setting status codes in the
        :class:`Redirect <litestar.response_containers.Redirect>` response container.
        This was previously only possible by setting the ``status_code`` parameter on
        the corresponding route handler, making dynamic redirect status codes and
        conditional redirects using this container hard to implement.

    .. change:: Sentinel value to support caching responses indefinitely
        :type: feature
        :pr: 1414
        :issue: 1365

        Add the :class:`CACHE_FOREVER <litestar.config.response_cache.CACHE_FOREVER>` sentinel value, that, when passed
        to a route handlers ``cache argument``, will cause it to be cached forever, skipping the default expiration.

        Additionally, add support for setting
        :attr:`ResponseCacheConfig.default_expiration <litestar.config.response_cache.ResponseCacheConfig>` to ``None``,
        allowing to cache values indefinitely by default when setting ``cache=True`` on a route handler.

    .. change:: `Accept`-header parsing and content negotiation
        :type: feature
        :pr: 1317

        Add an :attr:`accept <litestar.connection.Request.accept>` property to
        :class:`Request <litestar.connection.Request>`, returning the newly added
        :class:`Accept <litestar.datastructures.headers.Accept>` header wrapper, representing the requests ``Accept``
        HTTP header, offering basic content negotiation.

        .. seealso::
            :ref:`usage/responses:Content Negotiation`

    .. change:: Enhanced WebSockets support
        :type: feature
        :pr: 1402

        Add a new set of features for handling WebSockets, including automatic connection handling, (de)serialization
        of incoming and outgoing data analogous to route handlers and OOP based event dispatching.

        .. seealso::
            :doc:`/usage/websockets`

    .. change:: SQLAlchemy 1 plugin mutates app state destructively
        :type: bugfix
        :pr: 1391
        :issue: 1368

        When using the SQLAlchemy 1 plugin, repeatedly running through the application lifecycle (as done when testing
        an application not provided by a factory function), would result in a :exc:`KeyError` on the second pass.

        This was caused be the plugin's ``on_shutdown`` handler deleting the ``engine_app_state_key`` from the
        application's state on application shutdown, but only adding it on application init.

        This was fixed by adding performing the necessary setup actions on application startup rather than init.

    .. change:: Fix SQLAlchemy 1 Plugin - ``'Request' object has no attribute 'dict'``
        :type: bugfix
        :pr: 1389
        :issue: 1388

        An annotation such as

        .. code-block:: python

            async def provide_user(request: Request[User, Token, Any]) -> User:
                ...

        would result in the error ``'Request' object has no attribute 'dict'``.

        This was fixed by changing how ``get_plugin_for_value`` interacts with :func:`typing.get_args`

    .. change:: Support OpenAPI schema generation with stringized return annotation
        :type: bugfix
        :pr: 1410
        :issue: 1409

        The following code would result in non-specific and incorrect information being generated for the OpenAPI schema:

        .. code-block:: python

            from __future__ import annotations

            from starlite import Starlite, get


            @get("/")
            def hello_world() -> dict[str, str]:
                return {"hello": "world"}

        This could be alleviated by removing ``from __future__ import annotations``. Stringized annotations in any form
        are now fully supported.

    .. change:: Fix OpenAPI schema generation crashes for models with ``Annotated`` type attribute
        :type: bugfix
        :issue: 1372
        :pr: 1400

        When using a model that includes a type annotation with :class:`typing.Annotated` in a route handler, the
        interactive documentation would raise an error when accessed. This has been fixed and :class:`typing.Annotated`
        is now fully supported.

    .. change:: Support empty ``data`` in ``RequestFactory``
        :type: bugfix
        :issue: 1419
        :pr: 1420

        Add support for passing an empty ``data`` parameter to a
        :class:`RequestFactory <litestar.testing.RequestFactory>`, which would previously lead to an error.

    .. change:: ``create_test_client`` and ``crate_async_test_client`` signatures and docstrings to to match ``Litestar``
        :type: misc
        :pr: 1417

        Add missing parameters to :func:`create_test_client <litestar.testing.create_test_client>` and
        :func:`create_test_client <litestar.testing.create_async_test_client>`. The following parameters were added:

        - ``cache_control``
        - ``debug``
        - ``etag``
        - ``opt``
        - ``response_cache_config``
        - ``response_cookies``
        - ``response_headers``
        - ``security``
        - ``stores``
        - ``tags``
        - ``type_encoders``



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
        ``starlite.stores.registry.StoreRegistry`` has been introduced;
        It serves as a central place to manage stores and reduces the amount of
        configuration needed for various integrations.

        - Add ``stores`` kwarg to ``Starlite`` and ``AppConfig`` to allow seeding of the ``StoreRegistry``
        - Add ``Starlite.stores`` attribute, containing a ``StoreRegistry``
        - Change ``RateLimitMiddleware`` to use ``app.stores``
        - Change request caching to use ``app.stores``
        - Change server side sessions to use ``app.stores``
        - Move ``starlite.config.cache.CacheConfig`` to  ``starlite.config.response_cache.ResponseCacheConfig``
        - Rename ``Starlite.cache_config`` > ``Starlite.response_cache_config``
        - Rename ``AppConfig.cache_config`` > ``response_cache_config``
        - Remove ``starlite/cache`` module
        - Remove ``ASGIConnection.cache`` property
        - Remove ``Starlite.cache`` attribute

        .. attention::
            ``starlite.middleware.rate_limit.RateLimitMiddleware``,
            ``starlite.config.response_cache.ResponseCacheConfig``,
            and ``starlite.middleware.session.server_side.ServerSideSessionConfig``
            instead of accepting a ``storage`` argument that could be passed a ``Storage`` instance now have to be
            configured via the ``store`` attribute, accepting a string key for the store to be used from the registry.
            The ``store`` attribute has a unique default set, guaranteeing a unique
            ``starlite.stores.memory.MemoryStore`` instance is acquired for every one of them from the
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


    .. change:: Enhance CLI autodiscovery logic
        :type: feature
        :breaking:
        :pr: 1322

        Update the CLI :ref:`usage/cli:autodiscovery` to only consider canonical modules app and application, but every
        ``starlite.app.Starlite`` instance or application factory able to return a ``Starlite`` instance within
        those or one of their submodules, giving priority to the canonical names app and application for application
        objects and submodules containing them.

        .. seealso::
            :ref:`CLI autodiscovery <usage/cli:autodiscovery>`

    .. change:: Configurable exception logging and traceback truncation
        :type: feature
        :pr: 1296

        Add three new configuration options to ``starlite.logging.config.BaseLoggingConfig``:

        ``starlite.logging.config.LoggingConfig.log_exceptions``
            Configure when exceptions are logged.

            ``always``
                Always log exceptions

            ``debug``
                Log exceptions in debug mode only

            ``never``
                Never log exception

        ``starlite.logging.config.LoggingConfig.traceback_line_limit``
            Configure how many lines of tracback are logged

        ``starlite.logging.config.LoggingConfig.exception_logging_handler``
            A callable that receives three parameters - the ``app.logger``, the connection scope and the traceback
            list, and should handle logging

        .. seealso::
            ``starlite.logging.config.LoggingConfig``


    .. change:: Allow overwriting default OpenAPI response descriptions
        :type: bugfix
        :issue: 1292
        :pr: 1293

        Fix https://github.com/litestar-org/litestar/issues/1292 by allowing to overwrite
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

        ``after_request`` hooks were not being called automatically when a ``starlite.response.Response``
        instances was returned from a route handler directly.

        .. seealso::
            :ref:`after_request`


    .. change:: Fix ``SQLAlchemyPlugin`` raises error when using SQLAlchemy UUID
        :type: bugfix
        :pr: 1355

        An error would be raised when using the SQLAlchemy plugin with a
        `sqlalchemy UUID <https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.UUID>`_. This
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

        ``starlite.events.emitter.SimpleEventEmitter`` was updated to using an async worker, pulling
        emitted events from a queue and subsequently calling listeners. Previously listeners were called immediately,
        making the operation effectively "blocking".


    .. change:: Make ``BaseEventEmitterBackend.emit`` synchronous
        :type: misc
        :breaking:
        :pr: 1376

        ``starlite.events.emitter.BaseEventEmitterBackend``, and subsequently
        ``starlite.events.emitter.SimpleEventEmitter`` and
        ``starlite.app.Starlite.emit`` have been changed to synchronous function, allowing them to easily be
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

        The ``initial_state`` argument to ``starlite.app.Starlite`` has been replaced with a ``state`` keyword
        argument, accepting an optional ``starlite.datastructures.state.State`` instance.

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

        ``starlite.app.Starlite.from_config`` was added to the
        ``starlite.app.Starlite`` class which allows to construct an instance
        from an ``starlite.config.app.AppConfig`` instance.

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
        ``starlite.exceptions.ImproperlyConfiguredException``.

    .. change:: Generic application state
        :type: feature
        :pr: 1030

        ``starlite.connection.base.ASGIConnection`` and its subclasses are now generic on ``State``
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

        Storage backends for server-side sessions``starlite.cache.Cache``` have been unified and replaced
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
        ``starlite.security.base.AbstractSecurityConfig``, enabling support for customized
        ``type_encoders`` for example in ``starlite.contrib.jwt.jwt_auth.JWTAuth``.


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

        ``starlite.plugins.InitPluginProtocol``
            Hook into an application's initialization process

        ``starlite.plugins.SerializationPluginProtocol``
            Extend the serialization and deserialization capabilities of an application

        ``starlite.plugins.OpenAPISchemaPluginProtocol``
            Extend OpenAPI schema generation


    .. change::  Unify response headers and cookies
        :type: misc
        :breaking:
        :pr: 1209

        :ref:`usage/responses:Response Headers` and :ref:`usage/responses:Response Cookies` now have the same
        interface, along with the ``headers`` and ``cookies`` keyword arguments to
        ``starlite.response.Response``. They each allow to pass either a
        `:class:`Mapping[str, str] <typing.Mapping>`, e.g. a dictionary, or a :class:`Sequence <typing.Sequence>` of
        ``starlite.datastructures.response_header.ResponseHeader`` or
        ``starlite.datastructures.cookie.Cookie`` respectively.


    .. change:: Replace Pydantic models with dataclasses
        :type: misc
        :breaking:
        :pr: 1242

        Several Pydantic models used for configuration have been replaced with dataclasses or plain classes. This change
        should be mostly non-breaking, unless you relied on those configuration objects being Pydantic models. The changed
        models are:

        - ``starlite.config.allowed_hosts.AllowedHostsConfig``
        - ``starlite.config.app.AppConfig``
        - ``starlite.config.response_cache.ResponseCacheConfig``
        - ``starlite.config.compression.CompressionConfig``
        - ``starlite.config.cors.CORSConfig``
        - ``starlite.config.csrf.CSRFConfig``
        - ``starlite.logging.config.LoggingConfig``
        - ``starlite.openapi.OpenAPIConfig``
        - ``starlite.static_files.StaticFilesConfig``
        - ``starlite.template.TemplateConfig``
        - ``starlite.contrib.jwt.jwt_token.Token``
        - ``starlite.contrib.jwt.jwt_auth.JWTAuth``
        - ``starlite.contrib.jwt.jwt_auth.JWTCookieAuth``
        - ``starlite.contrib.jwt.jwt_auth.OAuth2Login``
        - ``starlite.contrib.jwt.jwt_auth.OAuth2PasswordBearerAuth``
        - ``starlite.contrib.opentelemetry.OpenTelemetryConfig``
        - ``starlite.middleware.logging.LoggingMiddlewareConfig``
        - ``starlite.middleware.rate_limit.RateLimitConfig``
        - ``starlite.middleware.session.base.BaseBackendConfig``
        - ``starlite.middleware.session.client_side.CookieBackendConfig``
        - ``starlite.middleware.session.server_side.ServerSideSessionConfig``
        - ``starlite.response_containers.ResponseContainer``
        - ``starlite.response_containers.File``
        - ``starlite.response_containers.Redirect``
        - ``starlite.response_containers.Stream``
        - ``starlite.security.base.AbstractSecurityConfig``
        - ``starlite.security.session_auth.SessionAuth``


    .. change:: SQLAlchemy plugin moved to ``contrib``
        :type: misc
        :breaking:
        :pr: 1252

        The ``SQLAlchemyPlugin` has moved to ``starlite.contrib.sqlalchemy_1.plugin`` and will only be compatible
        with the SQLAlchemy 1.4 release line. The newer SQLAlchemy 2.x releases will be supported by the
        ``contrib.sqlalchemy`` module.


    .. change:: Cleanup of the ``starlite`` namespace
        :type: misc
        :breaking:
        :pr: 1135

        The ``starlite`` namespace has been cleared up, removing many names from it, which now have to be imported from
        their respective submodules individually. This was both done to improve developer experience as well as reduce
        the time it takes to ``import starlite``.

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

        ``starlite.contrib.jwt.jwt_auth.JWTCookieAuth`` didn't set the ``domain`` configuration value on the response
        cookie.


    .. change:: Fix https://github.com/litestar-org/starlite/issues/1201: Can not serve static file in ``/`` path
        :type: bugfix
        :issue: 1201

        A validation error made it impossible to serve static files from the root path ``/`` .

    .. change:: Fix https://github.com/litestar-org/starlite/issues/1149: Middleware not excluding static path
        :type: bugfix
        :issue: 1149

        A middleware's ``exclude`` parameter would sometimes not be honoured if the path was used to serve static files
        using ``StaticFilesConfig``.
