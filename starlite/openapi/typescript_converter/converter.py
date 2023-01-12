from copy import copy
from typing import Any, List, Optional, Tuple, TypeVar, Union, cast

from pydantic import BaseModel
from pydantic_openapi_schema.v3_1_0 import (
    Components,
    OpenAPI,
    Operation,
    Parameter,
    Reference,
    RequestBody,
    Responses,
    Schema,
)

from starlite.enums import HttpMethod, ParamType
from starlite.openapi.typescript_converter.schema_parsing import parse_schema
from starlite.openapi.typescript_converter.types import (
    TypeScriptInterface,
    TypeScriptNamespace,
    TypeScriptPrimitive,
    TypeScriptProperty,
    TypeScriptType,
    TypeScriptUnion,
)

T = TypeVar("T", bound=BaseModel)


def deref(open_api_container: Union[T, dict], components: Components) -> Union[T, dict]:
    if isinstance(open_api_container, BaseModel):
        copied = open_api_container.copy()
        for field in open_api_container.__fields__:
            if value := getattr(copied, field, None):
                if isinstance(value, Reference):
                    setattr(copied, field, deref(resolve_ref(value, components=components), components=components))
                elif isinstance(value, (Schema, dict)):
                    setattr(copied, field, deref(value, components=components))
    else:
        copied = copy(open_api_container)
        for key, value in copied.items():
            if isinstance(value, Reference):
                copied[key] = deref(resolve_ref(value, components=components), components=components)
            elif isinstance(value, (Schema, dict)):
                copied[key] = deref(value, components=components)

    return copied


def resolve_ref(ref: Reference, components: Components) -> Schema:
    current: Any = components
    for path in [p for p in ref.ref.split("/") if p not in {"#", "components"}]:
        current = current[path] if isinstance(current, dict) else getattr(current, path, None)

    if not isinstance(current, Schema):  # pragma: no cover
        raise ValueError(
            f"unexpected value type, expected schema but received {type(current).__name__ if current is not None else 'None'}"
        )

    return current


def get_openapi_type(value: Optional[Union[Reference, T]], components: Components) -> Optional[T]:
    if isinstance(value, Reference):
        return deref(resolve_ref(value, components=components), components=components)
    return deref(value, components=components) if value else None


def parse_params(
    params: List[Parameter],
    components: Components,
) -> Tuple[TypeScriptInterface, ...]:
    cookie_params: List[TypeScriptProperty] = []
    header_params: List[TypeScriptProperty] = []
    path_params: List[TypeScriptProperty] = []
    query_params: List[TypeScriptProperty] = []

    for param in params:
        if schema := get_openapi_type(param.param_schema, components):
            ts_prop = TypeScriptProperty(key=param.name, required=param.required, value=parse_schema(schema))
            if param.param_in == ParamType.COOKIE:
                cookie_params.append(ts_prop)
            elif param.param_in == ParamType.HEADER:
                header_params.append(ts_prop)
            elif param.param_in == ParamType.PATH:
                path_params.append(ts_prop)
            else:
                query_params.append(ts_prop)

    result: List[TypeScriptInterface] = []

    if cookie_params:
        result.append(TypeScriptInterface("CookieParameters", tuple(cookie_params)))
    if header_params:
        result.append(TypeScriptInterface("HeaderParameters", tuple(header_params)))
    if path_params:
        result.append(TypeScriptInterface("PathParameters", tuple(path_params)))
    if query_params:
        result.append(TypeScriptInterface("QueryParameters", tuple(query_params)))

    return tuple(result)


def parse_body(body: RequestBody, components: Components) -> TypeScriptType:
    undefined = TypeScriptPrimitive("undefined")
    if body.required:
        return TypeScriptType("RequestBody", undefined)

    if (content := [get_openapi_type(v.media_type_schema, components) for v in body.content.values()]) and (
        schema := content[0]
    ):
        return TypeScriptType(
            "RequestBody",
            parse_schema(schema)
            if body.required
            else TypeScriptUnion((parse_schema(content[0]), TypeScriptPrimitive("undefined"))),
        )

    return TypeScriptType("RequestBody", undefined)


def parse_responses(responses: Responses, components: Components) -> Tuple[TypeScriptNamespace, ...]:
    result: List[TypeScriptNamespace] = []
    for http_status, response in responses.items():
        content = (
            [
                get_openapi_type(v.media_type_schema, components)
                for v in response.content.values()
                if v.media_type_schema
            ]
            if response.content
            else []
        )

        containers = [
            TypeScriptType("ResponseBody", parse_schema(content[0]) if content else TypeScriptPrimitive("undefined")),
            TypeScriptInterface(
                "ResponseHeaders",
                tuple(
                    [
                        TypeScriptProperty(
                            required=get_openapi_type(header, components=components).required,
                            key=key,
                            value=TypeScriptPrimitive("string"),
                        )
                        for key, header in response.headers.items()
                    ]
                ),
            )
            if response.headers
            else None,
        ]

        result.append(TypeScriptNamespace(f"Http{http_status}", (c for c in containers if c)))

    return tuple(result)


def convert_openapi_to_typescript(openapi_schema: OpenAPI, namespace: str = "API") -> TypeScriptNamespace:
    if not openapi_schema.paths:
        raise ValueError("OpenAPI schema has no paths")
    if not openapi_schema.components:
        raise ValueError("OpenAPI schema has no components")

    operations: List[TypeScriptNamespace] = []

    for path, path_item in openapi_schema.paths.items():
        shared_params = [
            get_openapi_type(p, components=openapi_schema.components) for p in (path_item.parameters or []) if p
        ]
        for method in HttpMethod:
            if operation := cast("Optional[Operation]", getattr(path_item, method.lower(), "None")):
                params = parse_params(
                    [
                        *(
                            get_openapi_type(p, components=openapi_schema.components)
                            for p in (operation.parameters or [])
                            if p
                        ),
                        *shared_params,
                    ],
                    components=openapi_schema.components,
                )
                request_body = (
                    parse_body(operation.requestBody, components=openapi_schema.components)
                    if operation.requestBody
                    else None
                )

                responses = parse_responses(operation.responses or {}, components=openapi_schema.components)

                operations.append(
                    TypeScriptNamespace(
                        operation.operationId,
                        tuple(container for container in (*params, request_body, *responses) if container),
                    )
                )

    return TypeScriptNamespace(namespace, tuple(operations))
