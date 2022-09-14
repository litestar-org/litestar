# Changelog

[1.18.1]

- fix `ResponseHeader` not being correctly encoded.
- Update `SQLAlchemyPlugin` for v2.0 compatibility.

[1.18.0]

- update `serializer` to handle `SecretStr`, `PurePath` and `PurePosixPath`.
- update multipart handling to use [starlite-multipart](https://github.com/starlite-api/starlite-multipart).

[1.17.2]

- update `Partial` to support dataclasses.

[1.17.1]

- add `url_for` method similar to Starlette's.
- fix `AsyncCallabled` to ensure wrapped methods remain unbound.

[1.17.0]

- add `SessionMiddleware`.

[1.16.2]

- fix `before_request` regression causing it to not handle returned responses from the hook.

[1.16.1]

- update `picologging` integration to use `picologging.dictConfig`.
- fix validation errors raised when using custom state.

[1.16.0]

- add `exclude` parameter to `AbstractAuthenticationMiddleware`.
- allow disabling OpenAPI documentation sites and schema endpoints via config.
- simplify `KwargsModel`.

[1.15.0]

- `examples/` directory and tests for complete documentation examples.
- replace `pydantic-openapi-schema` import from `v3_0_3` with import from `v3_10_0`.

[1.14.1]

- fix OpenAPI schema for `UploadFile`.
- integrate OpenAPI security definitions into OpenAPI configuration.
- remove empty aliases from field parameters.

[1.14.0]

- refactor: Simplified and improved brotli middleware typing.
- update: Extended `PluginProtocol` with an `on_app_init` method.

[1.13.1]

- fix `is_class_and_subclass` not handling type annotations.

[1.13.0]

- fix: remove duplicated detail in `HTTPException.__str__()`.
- fix: removed imports causing `MissingDependencyException` where `brotli` not installed and not required.
- update: Add `skip_validation` flag to `Dependency` function.
- update: Export starlite cookie to header and use it in CSRF middleware and OpenAPI response @seladb.
- update: cache protocol, cache backend integration including locking for sync access.
- update: consistent eager evaluation of async callables across the codebase.

[1.12.0]

- fix: handling of "\*" in routes by @waweber.
- update: middleware typing and addition of `DefineMiddleware`.

[1.11.1]

- hotfix: Exception raised by `issubclass` check.

[1.11.0]

- update: OpenAPIController to use render methods and configurable `root` class var @mobiusxs.
- fix: `UploadFile` OpenAPI schema exception.
- fix: `Stream` handling of generators.
- refactor: http and path param parsing.

[1.10.1]

- fix: regression in StaticFiles of resolution of index.html in `html_mode=True`.

[1.10.0]

- breaking: update handling of status code <100, 204 or 304.
- fix: adding only new routes to the route_map by @Dr-Emann.
- refactor: tidy up exceptions.
- refactor: update `to_response` and datastructures.
- refactor: update installation extras.

[1.9.2]

- update installation extras.

[1.9.1]

- add CSRF Middleware and config, @seladb.
- create starlite ports of BackgroundTask and BackgroundTasks in `starlite.datastructures`.

[1.9.0]

- ass support for [picologging](https://github.com/microsoft/picologging).
- update response headers, handling of cookies and handling of responses.

[1.8.1]

- add piccolo-orm plugin.
- fix CacheConfig being broken due to pydantic validation bug.

[1.8.0]

- \*_breaking_ replace [openapi-pydantic-schema](https://github.com/kuimono/openapi-schema-pydantic)
  with [pydantic-openapi-schema](https://github.com/starlite-api/pydantic-openapi-schema).
- add [Stoplights Elements](https://stoplight.io/open-source/elements) OpenAPI support @aedify-swi

[1.7.3]

- fix to routes being allowed under static paths and improvements to path resolution @Dr-Emann

[1.7.2]

- update `Partial` to annotate fields of nested classes @Harry-Lees.
- add `OpenAPIConfig.use_handler_docstring` param.

[1.7.1]

- add `Swagger-UI` support @timwedde.
- add orjson support to websockets.

[1.7.0]

- add `TortoiseORMPlugin`.

[1.6.2]

- update error handling,
- remove `exrex` from second hand dependencies.

[1.6.1]

- add `after_response` hook.

[1.6.0]

- add support for layered parameters.

[1.5.4]

- add Brotli compression middleware by @cofin.

[1.5.3]

- update path param validation during registration @danesolberg.
- fix route handler exception resolution.

[1.5.2]

- fix path resolution edge cases.

[1.5.1]

- add gzip middleware support.
- raise exception on routes with duplicate path parameters @danesolberg.
- fix dependency validation failure returning 400 (instead of 500).

[1.5.0]

- add layered middleware support.
- update exception handlers to work in layers.
- fix CORS headers and middlewares not processing exceptions.
- fix order of exception handlers.
- fix OpenAPI array items being double nested.
- make `requests` and optional dependency @Bobronium.

[1.4.2]

- fix `status_code` missing from exception OpenAPI documentation @timwedde.
- fix exception `extra` being mistyped in OpenAPI documentation.

[1.4.1]

- fix `Provide` properly detects async `@classmethod` as async callables.
- fix `None` return value from handler with `204` has empty response content.
- update exception handlers to be configurable at each layer of the application.
- add better detection of async callables.

[1.4.0]

- update Starlette to 0.20.3.
- add test for generic model injection @Goldziher.
- add selective deduplication of openapi parameters @peterschutt.
- add raise `ImproperConfiguredException` when user-defined generic type resolved as openapi parameter @peterschutt.
- add dependency function @peterschutt.

[1.3.9]

- include dependencies in docs @timwedde.

[1.3.8]

- fix `Router.tags` being omitted from the docs @peterschutt.

[1.3.7]

- fix logging configure hanging in startup.

[1.3.6]

- updated validation errors to return more useful json objects.

[1.3.5]

- update Starlette to 0.20.1.
- add memoization to openAPI schema.

[1.3.4]

- fix `DTOFactory` handling of optional fields @peterschutt.

[1.3.3]

- update pydantic to 1.9.1.

[1.3.2]

- fix static path resolution when static files are served from "/".
- refactor logging.

[1.3.1]

- fix reserved keywords appearing in OpenAPI documentation @Joko013.

[1.3.0]

- updated middleware call order @slavugan.

[1.2.5]

- fix request.body being only readable once by setting the read result into scope.

[1.2.4]

- updated `Starlette` to version `0.19.0`.

[1.2.3]

- update `LoggingConfig` to be non-blocking @madlad33.
- fix regression in error handling, returning 404 instead of 500.

[1.2.2]

- fix regression with controller multi-registration.

[1.2.1]

- fix handling of empty request body @t1waz.

[1.2.0]

- add run_in_thread configuration.

[1.1.1]

- added tags support to Controller @tclasen.
- updated OpenAPI operationIds to be more humanized @tclasen.

[1.1.0]

- added response caching support.

[1.0.5]

- fixed typing of `Partial` @to-ph.

[1.0.4]

- updated `Request.state` to be defined already in the application @ashwinvin.

[1.0.3]

- added argument validation on `Parameter` and `Body`.

[1.0.2]

- fixed lifecycle injection of application state into class methods.

[1.0.1]

- fixed `MissingDependencyException` inheritance chain.
- fixed `ValidationException` missing as export in `__init__` method.

[1.0.0]

- added template support @ashwinvin.
- updated `starlite.request` by renaming it to `starlite.connection`.
- updated the kwarg parsing and data injection logic to compute required kwargs for each route handler during
  application bootstrap.
- updated the redoc UI path from `/schema/redoc` to `/schema` @yudjinn.

[0.7.2]

- add missing support for starlette background tasks.
- fixed error with static files not working with root route.
- fixed function signature modelling ignoring non-annotated fields.
- fixed headers being case-sensitive.

[0.7.1]

- updated handling of paths without parameters.

[0.7.0]

- added `@asgi` route handler decorator.
- updated query parameters parsing.
- updated request-response cycle handling.
- updated rewrote route resolution.

[0.6.0]

- added support for multiple paths per route handler.
- added support for static files.
- updated `DTOFactory`.
- updated `PluginProtocol` - added `from_dict` methods.
- updated `SQLAlchemyPlugin`.
- updated dependency injection to allow for dependency injection into dependencies.
- updated lifecycle support to allow for application state injection.
- updated route handlers and dependencies to allow for application state injection.

[0.5.0]

- updated BaseRoute to not inherit from Starlette, allowing for optimization using `_slots_`.
- updated RouteHandlers from being pydantic models to being custom classes, allowing for optimization using `_slots_`.
- updated base path handling in controllers @vincentsarago.

[0.4.3]

- fixed dto factory handling of forward refs.

[0.4.2]

- fixed Parameter default not being respected.

[0.4.1]

- added support for `before_request` and `after_request` hooks.
- fixed sql_alchemy requirement not being isolated to the plugin only.

[0.4.0]

- added `DTOFactory`.
- added `SQLAlchemyPlugin`.
- added plugin support.
- fixed orjson compatibility @vincentsarago.

[0.3.0]

- updated openapi configuration.

[0.2.1]

- fixex regression in handler validation.

[0.2.0]

- added support for websockets.
- updated multipart data handling to support mixed fields.

[0.1.6]

- fixex monkey patch "openapi-schema-pydantic" to change Schema.Config.extra to Extra.ignore.

[0.1.5]

- fixed monkey patch "openapi-schema-pydantic" to change Schema.extra to Extra.ignore.

[0.1.4]

- fixex update pydantic-factories to v1.1.0, resolving compatibility issues with older versions of pydantic.
- fixex include_in_schema for routes always being true.

[0.1.3]

- updated dependencies to use pydantic-factories v1.0.0.
- added `NotFoundException`.

[0.1.2]

- fixed _requests_ not being included in project dependencies.
- updated pydantic to v1.9.0.

[0.1.1]

- added missing exports to **init**.

[0.1.0]

- initial release.
