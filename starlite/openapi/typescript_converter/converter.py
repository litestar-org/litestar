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
from starlite.openapi.typescript_converter.schema_parsing import (
    normalize_typescript_namespace,
    parse_schema,
)
from starlite.openapi.typescript_converter.types import (
    TypeScriptInterface,
    TypeScriptNamespace,
    TypeScriptPrimitive,
    TypeScriptProperty,
    TypeScriptType,
    TypeScriptUnion,
)

T = TypeVar("T", bound=Union[BaseModel, dict, list])


def _deref_model(model: BaseModel, components: Components) -> BaseModel:
    for field in model.__fields__:
        if value := getattr(model, field, None):
            if isinstance(value, Reference):
                setattr(model, field, deref_container(resolve_ref(value, components=components), components=components))
            elif isinstance(value, (Schema, (dict, list))):
                setattr(model, field, deref_container(value, components=components))
    return model


def _deref_dict(values: dict, components: Components) -> dict:
    for key, value in values.items():
        if isinstance(value, Reference):
            values[key] = deref_container(resolve_ref(value, components=components), components=components)
        elif isinstance(value, (Schema, (dict, list))):
            values[key] = deref_container(value, components=components)
    return values


def _deref_list(values: list, components: Components) -> list:
    for i, value in enumerate(values):
        if isinstance(value, Reference):
            values[i] = deref_container(resolve_ref(value, components=components), components=components)
        elif isinstance(value, (Schema, (dict, list))):
            values[i] = deref_container(value, components=components)
    return values


def deref_container(open_api_container: T, components: Components) -> T:
    """Dereference an object that may contain Reference instances.

    Args:
        open_api_container: Either an OpenAPI content, a dict or a list.
        components: The OpenAPI schema Components section.

    Returns:
        A dereferenced object.
    """

    if isinstance(open_api_container, BaseModel):
        return cast("T", _deref_model(open_api_container.copy(), components))

    if isinstance(open_api_container, dict):
        return cast("T", _deref_dict(copy(open_api_container), components))

    return cast("T", _deref_list(copy(open_api_container), components))  # type: ignore


def resolve_ref(ref: Reference, components: Components) -> Schema:
    """Resolve a reference object into the actual value it points at.

    Args:
        ref: A Reference instance.
        components: The OpenAPI schema Components section.

    Returns:
        An OpenAPI schema instance.
    """
    current: Any = components
    for path in [p for p in ref.ref.split("/") if p not in {"#", "components"}]:
        current = current[path] if isinstance(current, dict) else getattr(current, path, None)

    if not isinstance(current, Schema):  # pragma: no cover
        raise ValueError(
            f"unexpected value type, expected schema but received {type(current).__name__ if current is not None else 'None'}"
        )

    return current


def get_openapi_type(value: Union[Reference, T], components: Components) -> T:
    """Extract or dereference an OpenAPI container type.

    Args:
        value: Either a reference or a container type.
        components: The OpenAPI schema Components section.

    Returns:
        The extracted container.
    """
    if isinstance(value, Reference):
        return cast("T", deref_container(resolve_ref(value, components=components), components=components))
    return deref_container(value, components=components)


def parse_params(
    params: List[Parameter],
    components: Components,
) -> Tuple[TypeScriptInterface, ...]:
    """Parse request parameters.

    Args:
        params: An OpenAPI Operation parameters.
        components: The OpenAPI schema Components section.

    Returns:
        A tuple of resolved interfaces.
    """
    cookie_params: List[TypeScriptProperty] = []
    header_params: List[TypeScriptProperty] = []
    path_params: List[TypeScriptProperty] = []
    query_params: List[TypeScriptProperty] = []

    for param in params:
        if param.param_schema and (schema := get_openapi_type(param.param_schema, components)):
            ts_prop = TypeScriptProperty(
                key=normalize_typescript_namespace(param.name, allow_quoted=True),
                required=param.required,
                value=parse_schema(schema),
            )
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


def parse_request_body(body: RequestBody, components: Components) -> TypeScriptType:
    """Parse the schema request body.

    Args:
        body: An OpenAPI RequestBody instance.
        components: The OpenAPI schema Components section.

    Returns:
        A TypeScript type.
    """
    undefined = TypeScriptPrimitive("undefined")
    if not body.content:
        return TypeScriptType("RequestBody", undefined)

    if (
        content := [
            get_openapi_type(v.media_type_schema, components) for v in body.content.values() if v.media_type_schema
        ]
    ) and (schema := content[0]):
        return TypeScriptType(
            "RequestBody",
            parse_schema(schema) if body.required else TypeScriptUnion((parse_schema(content[0]), undefined)),
        )

    return TypeScriptType("RequestBody", undefined)


def parse_responses(responses: Responses, components: Components) -> Tuple[TypeScriptNamespace, ...]:
    """Parse a given Operation's Responses object.

    Args:
        responses: An OpenAPI Responses object.
        components: The OpenAPI schema Components section.

    Returns:
        A tuple of namespaces, mapping response codes to data.
    """
    result: List[TypeScriptNamespace] = []
    for http_status, response in [
        (status, get_openapi_type(res, components=components)) for status, res in responses.items()
    ]:
        if (
            response
            and response.content
            and (
                content := [
                    get_openapi_type(v.media_type_schema, components)
                    for v in response.content.values()
                    if v.media_type_schema
                ]
            )
        ):
            ts_type = parse_schema(content[0])
        else:
            ts_type = TypeScriptPrimitive("undefined")

        containers = [
            TypeScriptType("ResponseBody", ts_type),
            TypeScriptInterface(
                "ResponseHeaders",
                tuple(
                    TypeScriptProperty(
                        required=get_openapi_type(header, components=components).required,
                        key=normalize_typescript_namespace(key, allow_quoted=True),
                        value=TypeScriptPrimitive("string"),
                    )
                    for key, header in response.headers.items()
                ),
            )
            if response.headers
            else None,
        ]

        result.append(TypeScriptNamespace(f"Http{http_status}", tuple(c for c in containers if c)))

    return tuple(result)


def convert_openapi_to_typescript(openapi_schema: OpenAPI, namespace: str = "API") -> TypeScriptNamespace:
    """Convert an OpenAPI Schema instance to a TypeScript namespace. This function is the main entry point for the
    TypeScript converter.

    Args:
        openapi_schema: An OpenAPI Schema instance.
        namespace: The namespace to use.

    Returns:
        A string representing the generated types.
    """
    if not openapi_schema.paths:  # pragma: no cover
        raise ValueError("OpenAPI schema has no paths")
    if not openapi_schema.components:  # pragma: no cover
        raise ValueError("OpenAPI schema has no components")

    operations: List[TypeScriptNamespace] = []

    for path_item in openapi_schema.paths.values():
        shared_params = [
            get_openapi_type(p, components=openapi_schema.components) for p in (path_item.parameters or []) if p
        ]
        for method in HttpMethod:
            if (
                operation := cast("Optional[Operation]", getattr(path_item, method.lower(), "None"))
            ) and operation.operationId:
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
                    parse_request_body(
                        get_openapi_type(operation.requestBody, components=openapi_schema.components),
                        components=openapi_schema.components,
                    )
                    if operation.requestBody
                    else None
                )

                responses = parse_responses(operation.responses or {}, components=openapi_schema.components)

                operations.append(
                    TypeScriptNamespace(
                        normalize_typescript_namespace(operation.operationId, allow_quoted=False),
                        tuple(container for container in (*params, request_body, *responses) if container),
                    )
                )

    return TypeScriptNamespace(namespace, tuple(operations))
