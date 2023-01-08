from itertools import permutations
from typing import Any, Dict, List, Literal, Optional, Union, cast, overload

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


def create_any_of_union(any_of: List[Schema]) -> TypeScriptUnion:
    """Handle schema.anyOf values.

    AnyOf has a special logic, which means it correlates with any combination of the anyOf schema list.

    Args:
        any_of: A list of schemas.

    Returns:
        A typescript union.
    """
    num_of_permutations = len(any_of)
    parsed_schemas = [parse_schema(s) for s in any_of]
    variants: List[TypeScriptElement] = [*parsed_schemas]

    while num_of_permutations > 1:
        variants.extend(
            [
                TypeScriptIntersection(list(permutation))
                for permutation in permutations(parsed_schemas, num_of_permutations)
            ]
        )
        num_of_permutations -= 1

    return TypeScriptUnion(variants)


@overload
def create_interface(properties: Dict[str, Schema]) -> TypeScriptAnonymousInterface:
    ...


@overload
def create_interface(properties: Dict[str, Schema], name: str) -> TypeScriptInterface:
    ...


def create_interface(
    properties: Dict[str, Schema], name: Optional[str] = None
) -> Union[TypeScriptAnonymousInterface, TypeScriptInterface]:
    """Create a typescript interface from the given schema.properties values.

    Args:
        properties: schema.properties mapping.
        name: An optional string representing the interface name.

    Returns:
        A typescript interface or anonymous interface.
    """
    parsed_properties = [
        TypeScriptProperty(
            key=key, value=parse_schema(schema), required=key in schema.required if schema.required else True
        )
        for key, schema in properties.items()
    ]
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
        return TypeScriptUnion(types=[TypeScriptLiteral(value=value) for value in schema.enum])
    if schema.const:
        return TypeScriptLiteral(value=schema.const)
    if isinstance(schema.type, list):
        return TypeScriptUnion(
            [TypeScriptPrimitive(openapi_to_typescript_type_map[cast("OpenAPIType", s_type)]) for s_type in schema.type]
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
        return TypeScriptIntersection([parse_schema(s) for s in schema.allOf if is_schema_value(s)])
    if schema.oneOf:
        return TypeScriptUnion([parse_schema(s) for s in schema.oneOf if is_schema_value(s)])
    if schema.anyOf:
        return create_any_of_union([s for s in schema.anyOf if is_schema_value(s)])
    if is_schema_value(schema.items):
        return TypeScriptArray(parse_schema(schema.items))
    if schema.properties:
        return create_interface(properties={k: v for k, v in schema.properties.items() if is_schema_value(v)})
    return parse_type_schema(schema=schema)
