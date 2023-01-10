from typing import Any, Dict, Literal, Optional, Set, Union, cast, overload

from pydantic_openapi_schema.v3_1_0 import Schema
from typing_extensions import TypeGuard

from starlite.openapi.enums import OpenAPIType
from starlite.openapi.typescript_converter.types import (
    TypeScriptAnonymousInterface,
    TypeScriptArray,
    TypeScriptElement,
    TypeScriptInterface,
    TypeScriptIntersection,
    TypeScriptLiteral,
    TypeScriptPrimitive,
    TypeScriptProperty,
    TypeScriptUnion,
)

openapi_to_typescript_type_map: Dict[str, Literal["string", "boolean", "number", "null"]] = {
    OpenAPIType.STRING: "string",
    OpenAPIType.INTEGER: "number",
    OpenAPIType.NUMBER: "number",
    OpenAPIType.BOOLEAN: "boolean",
    OpenAPIType.NULL: "null",
}


def is_schema_value(value: Any) -> "TypeGuard[Schema]":
    """Typeguard for a schema value.

    Args:
        value: An arbitrary value

    Returns:
        A typeguard boolean dictating whether the passed in value is a Schema.
    """
    return isinstance(value, Schema)


@overload
def create_interface(properties: Dict[str, Schema], required: Optional[Set[str]]) -> TypeScriptAnonymousInterface:
    ...


@overload
def create_interface(properties: Dict[str, Schema], required: Optional[Set[str]], name: str) -> TypeScriptInterface:
    ...


def create_interface(
    properties: Dict[str, Schema], required: Optional[Set[str]] = None, name: Optional[str] = None
) -> Union[TypeScriptAnonymousInterface, TypeScriptInterface]:
    """Create a typescript interface from the given schema.properties values.

    Args:
        properties: schema.properties mapping.
        required: An optional list of required properties.
        name: An optional string representing the interface name.

    Returns:
        A typescript interface or anonymous interface.
    """
    parsed_properties = tuple(
        TypeScriptProperty(
            key=key, value=parse_schema(schema), required=key in required if required is not None else True
        )
        for key, schema in properties.items()
    )
    return (
        TypeScriptInterface(name=name, properties=parsed_properties)
        if name is not None
        else TypeScriptAnonymousInterface(properties=parsed_properties)
    )


def parse_type_schema(schema: Schema) -> Union[TypeScriptPrimitive, TypeScriptLiteral, TypeScriptUnion]:
    """Parse an OpenAPI schema representing a primitive type(s).

    Args:
        schema: An OpenAPI schema.

    Returns:
        A typescript type.
    """
    if schema.enum:
        return TypeScriptUnion(types=tuple(TypeScriptLiteral(value=value) for value in schema.enum))
    if schema.const:
        return TypeScriptLiteral(value=schema.const)
    if isinstance(schema.type, list):
        return TypeScriptUnion(
            tuple(
                TypeScriptPrimitive(openapi_to_typescript_type_map[cast("OpenAPIType", s_type)])
                for s_type in schema.type
            )
        )
    if schema.type in openapi_to_typescript_type_map:
        return TypeScriptPrimitive(openapi_to_typescript_type_map[schema.type])
    raise TypeError(f"received an unexpected openapi type: {schema.type}")  # pragma: no cover


def parse_schema(schema: Schema) -> TypeScriptElement:
    """Parse an OpenAPI schema object recursively to create typescript types.

    Args:
        schema: An OpenAPI Schema object.

    Returns:
        A typescript type.
    """
    if schema.allOf:
        return TypeScriptIntersection(tuple(parse_schema(s) for s in schema.allOf if is_schema_value(s)))
    if schema.oneOf:
        return TypeScriptUnion(tuple(parse_schema(s) for s in schema.oneOf if is_schema_value(s)))
    if is_schema_value(schema.items):
        return TypeScriptArray(parse_schema(schema.items))
    if schema.type == OpenAPIType.OBJECT:
        return create_interface(
            properties={k: v for k, v in schema.properties.items() if is_schema_value(v)} if schema.properties else {},
            required=set(schema.required) if schema.required else None,
        )
    return parse_type_schema(schema=schema)
