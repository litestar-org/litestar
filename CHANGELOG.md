[0.1.0]
- initial release


[0.1.1]
- added missing exports to __init__


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


[0.4.2]
- fixed Parameter default not being respected


[0.4.3]
- fixed dto factory handling of forward refs
