# Changelog

[0.1.0]

- initial release

[0.1.1]

- added missing exports to **init**

[0.1.2]

- fixed _requests_ not being included in project dependencies
- updated pydantic to v1.9.0

[0.1.3]

- updated dependencies to use pydantic-factories v1.0.0
- added `NotFoundException`

[0.1.4]

- fix: update pydantic-factories to v1.1.0, resolving compatibility issues with older versions of pydantic
- fix: include_in_schema for routes always being true

[0.1.5]

- fix: monkey patch "openapi-schema-pydantic" to change Schema.extra to Extra.ignore

[0.1.6]

- fix: monkey patch "openapi-schema-pydantic" to change Schema.Config.extra to Extra.ignore

[0.2.0]

- add support for websockets
- update multipart data handling to support mixed fields

[0.2.1]

- fix regression in handler validation

[0.3.0]

- updated openapi configuration:
  1. OpenAPI schema generation is now enabled by default
  2. The `OpenAPIController` is now part of the `OpenAPIConfig`
  3. The default schema download path changed from `/schema` to `/schema/openapi.json`
  4. Added a `/schema/openapi.yaml` route to the `OpenAPIController`

[0.4.0]

- fix orjson compatibility @vincentsarago
- added plugin support
- added `SQLAlchemyPlugin`
- added `DTOFactory`

[0.4.1]

- fixed sql_alchemy requirement not being isolated to the plugin only
- add support for `before_request` and `after_request` hooks

[0.4.2]

- fixed Parameter default not being respected

[0.4.3]

- fixed dto factory handling of forward refs

[0.5.0]

- updated base path handling in controllers @vincentsarago
- changed RouteHandlers from being pydantic models to being custom classes, allowing for optimization using `_slots_`
- changed BaseRoute to not inherit from Starlette, allowing for optimization using `_slots_`

[0.6.0]

- added support for multiple paths per route handler
- added support for static files
- updated lifecycle support to allow for application state injection
- updated route handlers and dependencies to allow for application state injection
- updated dependency injection to allow for dependency injection into dependencies
- updated `PluginProtocol` - added `from_dict` methods
- updated `SQLAlchemyPlugin`:
  1. added `from_dict` method
  2. all back-references are now typed as `Any`
  3. all relationships are now typed as `Optional`
- updated `DTOFactory`:
  1. supports generics
  2. added `to_model_instance` and `from_model_instance` methods
  3. added `field_definitions` kwarg, allowing for creating custom fields

[0.7.0]

- optimization: rewrote route resolution
- optimization: updated query parameters parsing
- optimization: updated request-response cycle handling
- added `@asgi` route handler decorator

[0.7.1]

- optimization: updated handling of paths without parameters

[0.7.2]

- add missing support for starlette background tasks
- fixed function signature modelling ignoring non-annotated fields
- fixed error with static files not working with root route
- fixed headers being case-sensitive
- minor code refactors

[1.0.0]

- optimization: rewrote the kwarg parsing and data injection logic to compute required kwargs for each route handler
  during application bootstrap
- added template support @ashwinvin
- changed the redoc UI path from `/schema/redoc` to `/schema` @yudjinn
- renamed `starlite.request` to `starlite.connection`

[1.0.1]

- fixed `MissingDependencyException` inheritance chain
- fixed `ValidationException` missing as export in `__init__` method

[1.0.2]

- fixed lifecycle injection of application state into class methods

[1.0.3]

- added argument validation on `Parameter` and `Body`

[1.0.4]

- updated `Request.state` to be defined already in the application @ashwinvin

[1.0.5]

- fixed typing of `Partial` @to-ph

[1.1.0]

- added response caching support

[1.1.1]

- added tags support to Controller @tclasen
- updated OpenAPI operationIds to be more humanized @tclasen

[1.2.0]

- add run_in_thread configuration

[1.2.1]

- fix handling of empty request body @t1waz

[1.2.2]

- fix regression with controller multi-registration

[1.2.3]

- update `LoggingConfig` to be non-blocking @madlad33
- fix regression in error handling, returning 404 instead of 500

[1.2.4]

- updated `Starlette` to version `0.19.0`

[1.2.5]

- fix request.body being only readable once by setting the read result into scope

[1.3.0]

- updated middleware call order @slavugan

[1.3.1]

- fix reserved keywords appearing in OpenAPI documentation @Joko013

[1.3.2]

- fix static path resolution when static files are served from "/"
- refactor logging

[1.3.3]

- update pydantic to 1.9.1

[1.3.4]

- fix `DTOFactory` handling of optional fields @peterschutt

[1.3.5]

- update Starlette to 0.20.1
- add memoization to openAPI schema

[1.3.6]

- updated validation errors to return more useful json objects

[1.3.7]

- fix logging configure hanging in startup

[1.3.8]

- fix `Router.tags` being omitted from the docs @peterschutt

[1.3.9]

- include dependencies in docs @timwedde

[1.4.0]

- update Starlette to 0.20.3
- added test for generic model injection @Goldziher
- selective deduplication of openapi parameters @peterschutt
- raise improper configuration when user-defined generic type resolved as openapi parameter @peterschutt
- dependency function @peterschutt

[1.4.1]

- fix `Provide` properly detects async `@classmethod` as async callables
- fix `None` return value from handler with `204` has empty response content
- update exception handlers to be configurable at each layer of the application
- add better detection of async callables

[1.4.2]

- fix `status_code` missing from exception OpenAPI documentation @timwedde
- fix exception `extra` being mistyped in OpenAPI documentation

[1.5.0]

- add layered middleware support
- update exception handlers to work in layers
- fix CORS headers and middlewares not processing exceptions
- fix order of exception handlers
- fix OpenAPI array items being double nested
- make `requests` and optional dependency @Bobronium

[1.5.1]

- add gzip middleware support
- raise exception on routes with duplicate path parameters @danesolberg
- fix dependency validation failure returning 400 (instead of 500)

[1.5.2]

- fix path resolution edge cases

[1.5.3]

- Improve path param validation during registration @danesolberg
- Fix route handler exception resolution

[1.5.4]

- Add Brotli compression middleware by @cofin

[1.6.0]

- Add support for layered parameters

[1.6.1]

- Add `after_response` hook

[1.6.2]

- Update error handling
- Remove `exrex` from second hand dependencies

[1.7.0]

- Add `TortoiseORMPlugin`

[1.7.1]

- Add `Swagger-UI` support @timwedde
- Add orjson support to websockets

[1.7.2]

- Allow `Partial` to annotate fields of nested classes @Harry-Lees
- Add `OpenAPIConfig.use_handler_docstring` param

[1.7.3]

- Fix to routes being allowed under static paths and improvements to path resolution @Dr-Emann

[1.8.0]

- Breaking: Replace [openapi-pydantic-schema](https://github.com/kuimono/openapi-schema-pydantic)
  with [pydantic-openapi-schema](https://github.com/starlite-api/pydantic-openapi-schema).
- [Stoplights Elements](https://stoplight.io/open-source/elements) OpenAPI support @aedify-swi
