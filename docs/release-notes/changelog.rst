1.x Changelog
=============

1.51.16
-------

* Fix a security issue ([CVE-2024-32982](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-32982) where static files could allow users the ability to escape the configured static files directory
  and read arbitrary files on the filesystem.

1.51.11
-------

* Fix missing ``content-encoding`` headers for gzip/brotli compressed files

1.51.10
-------

* Fix ``Partial`` modifying dataclasses
* Fix CLI `--reload` flag not working as expected
* Add uvicorn to ``cli`` extra

1.51.9
------

* Remove ``pytest-lazy-fixture`` as s dependency that was erroneously added in the previous release


1.51.8
------

* Fix a regression where setting ``cache=True`` in a route handler would cause errors when used with the redis cache backend


1.51.7
------

* Fix a regression in path resolution that prevented ``404`` being raised for some invalid paths
* Fix a ``DeprecationWarning`` for the wrong name ``starlite/middleware/session/__init__.py``


1.51.6
------

- Fix optional query parameter openapi schema generation

1.51.5
------

- Fix domain configuration handling in JWT Auth

1.51.4
------

- support passing type encoders to ``AbstractSecurityConfig``

1.51.3
------

- Fix static path validation for ``/``

1.51.2
------

- Fix for security advisory https://github.com/starlite-api/starlite/security/advisories/GHSA-p24m-863f-fm6q

1.51.1
------

- Fix critical bug in parsing headers @knowsuchagency

1.51.0
-------

- fix optional sequence query param
- fix memory leak in logging middleware
- add missing CORS headers on exception responses
- configure logger and force "DEBUG" level in debug mode
- allow on-app-init hooks to modify initial state
- add exception logging in debug mode

1.50.2
------

- return valid OAuth2 response body by default
- correctly handle async-callable classes as dependencies
- fix ``type_encoders`` pickle bug when using response caching

1.50.1
------

- fix typo in jinja extra


1.50.0
------

- fix expected OpenAPI components in ``test_merged_components_correct``
- fix missing / wrong dependencies for Jinja2 extra
- add msgspec typed decoding
- add async test client
- prioritize plugins when creating DTOs

1.49.0
-------

- add reserved handler kwarg `body`
- add support for `Path` alongside `PurePath` for serialization
- add CLI commands for OpenAPI to TypeScript and OpenAPI schema generation
- ensure HTTP requests with invalid payloads return 400.
- ensure unique OpenAPI operation IDs
- fix issue when response is an empty iterable of DTOs
- fix `meter` in OpenTelemetry middleware being passed a

1.48.1
------
-  rename ``enc_hook`` -> ``default`` in ``encode_json``
-  re-enable ``super()`` calls to ``Response.serializer``
-  extend serializable type
-  support application factory pattern in CLI ``run`` command

1.48.0
------

-  add docs versioning.
-  add support for layered ``type_encoders``.
-  fix Sorting of tags in OpenAPI schema.
-  fix rendering of Enum params in OpenAPI.
-  fix swagger check for schema.
-  update ``fast-query-parsers`` and ``pydantic``.

1.47.0
------

-  fix Don’t import ``CookieBackendConfig`` by default in ``starlite.middleware.sessions``.
-  add Auto generation of DTOs from response data.
-  add Media type inference to HTTP handlers.
-  add Support differently named path parameters.
-  add ``fast-query-parsers``.


1.46.0
------

-  add CLI.
-  add Support ``Cookie`` instances in ``Response.set_cookie``.
-  add Support for controlling Pydantic models’ alias in OpenAPI Schema.
-  fix Jinja Template response ignores MediaType settings.
-  fix Make SessionAuth openapi_schema use backend_config.key.
-  fix Support utf-8 encoded strings in form data.
-  update Move ``JinjaTemplateEngine`` and ``MakoTemplateEngine`` to contrib.
-  update Update template config.



1.45.1
------

-  fix controller support for mixed websocket and http route handlers.
-  fix serialization of pydantic types.



1.45.0
------

-  add ``MessagePack`` support and serialization with ``msgspec``.
-  fix OpenAPI support for custom responses with generic types.
-  fix OpenAPI support for dynamic route handlers.
-  fix TestClient handling of escaped ampersands in query params.
-  fix logger propagation causing duplicate messages.
-  fix mounting starlette apps require trailing slashes.
-  fix rate-limiting of mount paths.



1.44.0
------

-  add support for pagination.
-  add new multipart parser.
-  update ``urlencoded`` parsing.
-  fix ``OpenAPIController`` when ASGI ``root_path`` is set on ASGI server.
-  fix generator based dependencies cached responses.



1.43.1
------

-  change ``StructLoggingConfing.processor`` type hint to ``List``.
-  fix cookie caching issues.
-  honour documentation_only flag for cookies.
-  remove ``SessionAuth`` import.
-  support legacy OpenAPI file upload format.



1.43.0
------

-  add security module and JWT auth contrib.
-  deprecate ``middleware.session.memcached_backend.MemcachedBackend.delete_all``.



1.42.0
------

-  support different types of path parameters for different leaf nodes.
-  add dependencies with ``yield``.
-  update custom state injection and add ``ImmutableState``.
-  fix #854 - Incorrect path resolution of ‘path’ type parameters.
-  fix #849 - Make LoggingMiddleware handle request bodies correctly.



1.41.0
------

-  general performance optimization.
-  fix #841: change ``middleware.session.sqlalchemy_backend.SessionModelMixin.data`` to ``LargeBinary``.



1.40.1
------

-  fix for improper parsing of sequence query params declared in nested dependencies.
-  fix for header parsing from iterables.



1.40.0
------

-  add ``OpenTelemetry`` instrumentation contrib package.
-  add forward ref resolution to signature models, allowing for usage with future annotations.
-  add handling of compressed “body” in logging middleware.
-  breaking: removed per request dependency caching.
-  fix 404 where current node has handlers and child route has path params.
-  fix flaky SQLA-session-backend tests.
-  update OpenAPI generation to hide automatically created OPTIONS routes in schema.
-  update ``AllowedHosts`` and ``CompressionMiddleware`` application to handler level.
-  update ``request_factory.{_default_route_handler,default_app}`` to have deferred bootstrap.
-  update the routing layer and param parsing to improve performance.



1.39.0
------

-  add ``CORSMiddleware``.
-  add ``URL``, ``URLPath`` and ``Address`` datastructures.
-  add ``send_as_attachment`` flag for ``StaticFiles``.
-  add handling of ``OPTIONS`` requests.
-  fix ``content-disposition`` in ``html_mode`` StaticFiles.
-  fix ``filename`` parameter in ``FileResponse`` set for ``StaticFiles`` response.
-  refactor builtin middlewares.
-  remove Python 3.7 support.
-  remove ``starlette`` as a dependency.



1.38.0
------

-  add ``AllowedHostsMiddleware``.
-  add ``*args`` override to ``Logger`` protocol.
-  add ``QueryMultiDict`` for ``request.query`` and ``socket.query``.
-  add ``ServerErrorMiddleware`` with own exception printer.
-  fix resolving starlette responses.
-  update ``path_params`` key to always exist in scope.



1.37.0
------

-  add ‘gzip’ compression.
-  add ``StaticFiles`` to replace Starlette’s version + support for ``fsspec``.
-  add ``head`` decorator.
-  remove Starlette ``Middleware`` type from typing.



1.36.0
------

-  add ``AbstractMiddleware`` class.
-  add layering for opt dictionary.
-  add per request caching of dependencies.
-  add\ ``Headers``, ``MutableHeaders`` and update ``FormMultiDict`` to use the ``multidict`` library.
-  fix asgi/websocket handlers when **future** annotations is used.
-  removed “method” from ``ResponseExtractorField``.
-  update dependency resolution in kwargs model to run concurrently.



1.35.1
------

-  fix hard dependency on external ``cryptography`` package when importing ``starlite``
-  fix invalid default ``base_url`` for ``TestClient``



1.35.0
------

-  add context-manager when using SQLAlchemy sessions.
-  add support for mounting ASGI applications.
-  fix ``SQLAlchemyPlugin.to_dict()`` where instance has relationship raising an exception.
-  update route registration to ensure unique handlers.
-  update routing logic to use a cleaner architecture.
-  update sessions to support explicitly setting to ``Empty``.
-  update test client to run session creation in the client’s portal.



1.34.0
------

-  add a ``__test__ = False`` attribute to the ``TestClient`` so it won’t get collected by pytest together with an async test.
-  add support for server-side sessions.
-  fix an issue where header values would be forced to lower case.



1.33.0
------

-  add ``TestClient`` to replace Starlette.



1.32.0
------

-  add ``BackgroundTask`` and ``BackgroundTasks`` to replace Starlette.
-  add ``Etag`` support to ``File`` and update response containers.
-  add ``RedirectResponse``, ``FileResponse`` and ``StreamingResponse`` to replace Starlette.
-  add ``status_codes`` constants.
-  fix cache classes being coupled to ``asyncio``.
-  update ``Response`` to replace Starlette.



1.31.0
------

-  add support for ETag headers.
-  add support Cache-Control headers.
-  fix ``Partial`` handling of ``ClassVar``.
-  update CSRFMiddleware to support excluding routes.



1.30.0
------

-  add ``url_for_static_asset`` path resolver function.
-  fix SQLAlchemy plugin maps JSON column types to ``Union[Dict, List]`` on DTOs.
-  fix ``SessionMiddleware`` handling non-session cookies with ``session`` anywhere in their name.
-  update a ``TypeVar`` for ``ExceptionHandler`` exception parameter.



1.29.0
------

-  add native support for ``TypedDict`` as data type.



1.28.1
------

-  fix ``QueueListenerHandler`` using stdlib ``QueueListenerHandler``.
-  update ``pydantic-factories`` to ``v1.11.1``.



1.28.0
------

-  add ``csrf_input`` template context value.
-  add ``csrf_token`` template callable.
-  add support for pydantic’s ``ConstrainedDate`` in OpenAPI schema.
-  fix ``NoReturn`` as allowed return typing for ``delete`` decorators.
-  fix signature model for dependency with ``skip_validation`` and ``default``.
-  update ``QueueListenerHandler`` to log to stderr by default.
-  update ``TemplateEngineProtocol`` to support registering template callables.



1.27.0
------

-  add ``url_for`` function in templates.
-  add ``redis`` cache backend.
-  add ``memcached`` cache backend.



1.26.1
------

-  fix optional ``UploadFile`` not being allowed.



1.26.0
------

-  add ``cache`` property getter to ``ASGIConnection``.
-  add support for creating test sessions from raw session cookies.
-  add support for using custom ``Request`` and ``WebSocket`` classes.
-  fix large file uploads with ``httpx``.
-  fix route handler name indexing.
-  update OpenAPIController to configure bundle download paths.
-  update ``RequestFactory`` to assign empty session dict by default.
-  update ``SQLAlchemyConfig`` session\ *maker*\ \* attributes to protocols.
-  update ``SQLAlchemyConfig`` to support either passing an instance or setting connection string.
-  update templating to inject request into template context.



1.25.0
------

-  add ``app.route_reverse`` method.
-  update ``SQLAlchemyPluginConfig`` to allow setting ``before_send_handler``.
-  update ``SQLAlchemyPluginConfig`` to expose ``engine`` and ``sessionmaker``.
-  update ``SQLAlchemyPlugin`` to handle ``SQLAlchemy 2.0`` column types.



1.24.0
------

-  update ``RequestFactory``.
-  update ``SQLAlchemyPlugin`` to support connection and dependency injection.



1.23.1
------

-  fix ``httpx`` being a required dependency.



1.23.0
------

-  add ``LoggingMiddleware``.
-  add support for configurable ``exclude_from_auth`` to ``AbstractAuthenticationMiddleware``.
-  refactor to reduce cognitive complexity of code and increase performance.



1.22.0
------

-  add ``**kwargs`` support to route handlers.
-  breaking: remove ``create_test_request``.
-  breaking: update Starlette to version ``0.21.0``. This version changes the TestClient to use ``httpx`` instead of ``requests``, which is a breaking change.
-  fix add default empty session to ``RequestFactory``.



1.21.2
------

-  fix regression in accessing ``request.headers`` due to caching.



1.21.1
------

-  add ``StructLoggingConfig``.



1.21.0
------

-  add ``on_app_init`` hook.
-  add ``testing.RequestFactory`` helper class for constructing ``Request`` objects.
-  refactor logging config and fix default handlers.
-  update ``State`` object implements ``MutableMapping`` interface, attribute access/mutation, ``copy()`` and ``dict()`` methods.
-  update internal implementations of ``HTTPConnection``, ``Request`` and ``WebSocket``.
-  update typing of ``__init__()`` method return annotations.



1.20.0
------

-  update ASGI typings (``scope``, ``receive``, ``send``, ``message`` and ``ASGIApp``) to use strong types derived from `asgiref <https://github.com/django/asgiref>`__.
-  update ``SessionMiddleware`` to use custom serializer used on request.
-  update ``openapi-pydantic-schema`` to ``v1.3.0`` adding support for ``__schema_name__``.



1.19.0
------

-  add ``RateLimitMiddleware``.
-  add ``media_type`` to ``ResponseContainer``.
-  add support for multiple cookies in ``create_test_request``.
-  add support for multiple responses documentation by @seladb.



1.18.1
------

-  fix ``ResponseHeader`` not being correctly encoded.
-  update ``SQLAlchemyPlugin`` for v2.0 compatibility.



1.18.0
------

-  update ``serializer`` to handle ``SecretStr``, ``PurePath`` and ``PurePosixPath``.
-  update multipart handling to use `starlite-multipart <https://github.com/starlite-api/starlite-multipart>`__.



1.17.2
------

-  update ``Partial`` to support dataclasses.



1.17.1
------

-  add ``url_for`` method similar to Starlette’s.
-  fix ``AsyncCallable`` to ensure wrapped methods remain unbound.



1.17.0
------

-  add ``SessionMiddleware``.



1.16.2
------

-  fix ``before_request`` regression causing it to not handle returned responses from the hook.



1.16.1
------

-  fix validation errors raised when using custom state.
-  update ``picologging`` integration to use ``picologging.dictConfig``.



1.16.0
------

-  add ``exclude`` parameter to ``AbstractAuthenticationMiddleware``.
-  add options to disable OpenAPI documentation sites and schema endpoints via config.
-  refactor ``KwargsModel``.



1.15.0
------

-  add ``examples/`` directory and tests for complete documentation examples.
-  replace ``pydantic-openapi-schema`` import from ``v3_0_3`` with import from ``v3_10_0``.



1.14.1
------

-  fix OpenAPI schema for ``UploadFile``.
-  remove empty aliases from field parameters.
-  update OpenAPI security definitions into OpenAPI configuration.



1.14.0
------

-  refactored brotli middleware typing.
-  update Extended ``PluginProtocol`` with an ``on_app_init`` method.



1.13.1
------

-  fix ``is_class_and_subclass`` not handling type annotations.



1.13.0
------

-  fix remove duplicated detail in ``HTTPException.__str__()``.
-  fix removed imports causing ``MissingDependencyException`` where ``brotli`` not installed and not required.
-  update Add ``skip_validation`` flag to ``Dependency`` function.
-  update Export starlite cookie to header and use it in CSRF middleware and OpenAPI response @seladb.
-  update cache protocol, cache backend integration including locking for sync access.
-  update consistent eager evaluation of async callables across the codebase.



1.12.0
------

-  fix handling of “\*” in routes by @waweber.
-  update middleware typing and addition of ``DefineMiddleware``.



1.11.1
------

-  hotfix Exception raised by ``issubclass`` check.



1.11.0
------

-  fix ``Stream`` handling of generators.
-  fix ``UploadFile`` OpenAPI schema exception.
-  refactor http and path param parsing.
-  update OpenAPIController to use render methods and configurable ``root`` class var @mobiusxs.



1.10.1
------

-  fix regression in StaticFiles of resolution of index.html in ``html_mode=True``.



1.10.0
------

-  breaking update handling of status code <100, 204 or 304.
-  fix adding only new routes to the route_map by @Dr-Emann.
-  refactor tidy up exceptions.
-  refactor update ``to_response`` and datastructures.
-  refactor update installation extras.



1.9.2
-----

-  update installation extras.



1.9.1
-----

-  add CSRF Middleware and config, @seladb.
-  add starlite ports of BackgroundTask and BackgroundTasks in ``starlite.datastructures``.



1.9.0
-----

-  add support for `picologging <https://github.com/microsoft/picologging>`__.
-  update response headers, handling of cookies and handling of responses.



1.8.1
-----

-  add piccolo-orm plugin.
-  fix CacheConfig being broken due to pydantic validation bug.



1.8.0
-----

-  add `Stoplights Elements <https://stoplight.io/open-source/elements>`__ OpenAPI support @aedify-swi
-  breaking replace `openapi-pydantic-schema <https://github.com/kuimono/openapi-schema-pydantic>`__ with `pydantic-openapi-schema <https://github.com/starlite-api/pydantic-openapi-schema>`__.



1.7.3
-----

-  fix to routes being allowed under static paths and improvements to path resolution @Dr-Emann



1.7.2
-----

-  add ``OpenAPIConfig.use_handler_docstring`` param.
-  update ``Partial`` to annotate fields of nested classes @Harry-Lees.



1.7.1
-----

-  add ``Swagger-UI`` support @timwedde.
-  add orjson support to websockets.



1.7.0
-----

-  add ``TortoiseORMPlugin``.



1.6.2
-----

-  remove ``exrex`` from second hand dependencies.
-  update error handling,



1.6.1
-----

-  add ``after_response`` hook.



1.6.0
-----

-  add support for layered parameters.



1.5.4
-----

-  add Brotli compression middleware by @cofin.



1.5.3
-----

-  fix route handler exception resolution.
-  update path param validation during registration @danesolberg.



1.5.2
-----

-  fix path resolution edge cases.



1.5.1
-----

-  add gzip middleware support.
-  fix dependency validation failure returning 400 (instead of 500).
-  fix raise exception on routes with duplicate path parameters @danesolberg.



1.5.0
-----

-  add ``requests`` as optional dependency @Bobronium.
-  add layered middleware support.
-  fix CORS headers and middlewares not processing exceptions.
-  fix OpenAPI array items being double nested.
-  fix order of exception handlers.
-  update exception handlers to work in layers.



1.4.2
-----

-  fix ``status_code`` missing from exception OpenAPI documentation @timwedde.
-  fix exception ``extra`` being mistyped in OpenAPI documentation.



1.4.1
-----

-  add better detection of async callables.
-  fix ``None`` return value from handler with ``204`` has empty response content.
-  fix ``Provide`` properly detects async ``@classmethod`` as async callables.
-  update exception handlers to be configurable at each layer of the application.



1.4.0
-----

-  add dependency function @peterschutt.
-  add raise ``ImproperConfiguredException`` when user-defined generic type resolved as openapi parameter @peterschutt.
-  add selective deduplication of openapi parameters @peterschutt.
-  add test for generic model injection @Goldziher.
-  update Starlette to 0.20.3.



1.3.9
-----

-  include dependencies in docs @timwedde.



1.3.8
-----

-  fix ``Router.tags`` being omitted from the docs @peterschutt.



1.3.7
-----

-  fix logging configure hanging in startup.



1.3.6
-----

-  update validation errors to return more useful json objects.



1.3.5
-----

-  add memoization to openAPI schema.
-  update Starlette to 0.20.1.



1.3.4
-----

-  fix ``DTOFactory`` handling of optional fields @peterschutt.



1.3.3
-----

-  update pydantic to 1.9.1.



1.3.2
-----

-  fix static path resolution when static files are served from “/”.
-  refactor logging.



1.3.1
-----

-  fix reserved keywords appearing in OpenAPI documentation @Joko013.



1.3.0
-----

-  update middleware call order @slavugan.



1.2.5
-----

-  fix ‘request.body()’ being only readable once by setting the read result into scope.



1.2.4
-----

-  update ``Starlette`` to version ``0.19.0``.



1.2.3
-----

-  fix regression in error handling, returning 404 instead of 500.
-  update ``LoggingConfig`` to be non-blocking @madlad33.



1.2.2
-----

-  fix regression with controller multi-registration.



1.2.1
-----

-  fix handling of empty request body @t1waz.



1.2.0
-----

-  add run_in_thread configuration.



1.1.1
-----

-  add tags support to Controller @tclasen.
-  update OpenAPI operationIds to be more humanized @tclasen.



1.1.0
-----

-  add response caching support.



1.0.5
-----

-  fix typing of ``Partial`` @to-ph.



1.0.4
-----

-  update ``Request.state`` to be defined already in the application @ashwinvin.



1.0.3
-----

-  add argument validation on ``Parameter`` and ``Body``.



1.0.2
-----

-  fix lifecycle injection of application state into class methods.



1.0.1
-----

-  fix ``MissingDependencyException`` inheritance chain.
-  fix ``ValidationException`` missing as export in ``__init__`` method.



1.0.0
-----

-  add template support @ashwinvin.
-  update ``starlite.request`` by renaming it to ``starlite.connection``.
-  update the kwarg parsing and data injection logic to compute required kwargs for each route handler during application bootstrap.
-  update the redoc UI path from ``/schema/redoc`` to ``/schema`` @yudjinn.



0.7.2
-----

-  add missing support for starlette background tasks.
-  fix error with static files not working with root route.
-  fix function signature modelling ignoring non-annotated fields.
-  fix headers being case-sensitive.



0.7.1
-----

-  update handling of paths without parameters.



0.7.0
-----

-  add ``@asgi`` route handler decorator.
-  update query parameters parsing.
-  update request-response cycle handling.
-  update rewrote route resolution.



0.6.0
-----

-  add support for multiple paths per route handler.
-  add support for static files.
-  update ``DTOFactory``.
-  update ``PluginProtocol`` - add ``from_dict`` methods.
-  update ``SQLAlchemyPlugin``.
-  update dependency injection to allow for dependency injection into dependencies.
-  update lifecycle support to allow for application state injection.
-  update route handlers and dependencies to allow for application state injection.



0.5.0
-----

-  update BaseRoute to not inherit from Starlette, allowing for optimization using ``_slots_``.
-  update RouteHandlers from being pydantic models to being custom classes, allowing for optimization using ``_slots_``.
-  update base path handling in controllers @vincentsarago.



0.4.3
-----

-  fix dto factory handling of forward refs.



0.4.2
-----

-  fix Parameter default not being respected.



0.4.1
-----

-  add support for ``before_request`` and ``after_request`` hooks.
-  fix sql_alchemy requirement not being isolated to the plugin only.



0.4.0
-----

-  add ``DTOFactory``.
-  add ``SQLAlchemyPlugin``.
-  add plugin support.
-  fix orjson compatibility @vincentsarago.



0.3.0
-----

-  update openapi configuration.



0.2.1
-----

-  fix regression in handler validation.



0.2.0
-----

-  add support for websockets.
-  update multipart data handling to support mixed fields.



0.1.6
-----

-  fix monkey patch “openapi-schema-pydantic” to change Schema.Config.extra to Extra.ignore.



0.1.5
-----

-  fix monkey patch “openapi-schema-pydantic” to change Schema.extra to Extra.ignore.



0.1.4
-----

-  fix include_in_schema for routes always being true.
-  fix update pydantic-factories to v1.1.0, resolving compatibility issues with older versions of pydantic.



0.1.3
-----

-  add ``NotFoundException``.
-  update dependencies to use pydantic-factories v1.0.0.



0.1.2
-----

-  fix ``requests`` not being included in project dependencies.
-  update pydantic to v1.9.0.



0.1.1
-----

-  add missing exports to **init**.



0.1.0
-----

-  initial release.
