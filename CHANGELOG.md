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
