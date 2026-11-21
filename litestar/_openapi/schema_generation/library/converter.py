from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from litestar._openapi.schema_generation.library.exceptions import SchemaConversionError
from litestar._openapi.schema_generation.utils import nullable_scalar
from litestar.openapi.spec.discriminator import Discriminator
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.reference import Reference
from litestar.openapi.spec.schema import Schema

__all__ = ("json_schema_to_spec",)

_RefResolver = Callable[[str], Schema | Reference]
EMBED_PREFIX = "litestar-embed:"
_ATTRIBUTES = {**Schema.field_aliases(), "exclusiveMaximum": "exclusive_maximum"}
_ANNOTATIONS = frozenset({"title", "description", "default", "examples", "deprecated", "read_only", "write_only"})

_SUBSCHEMA_KEYS = frozenset(
    {
        "items",
        "contains",
        "not",
        "if",
        "then",
        "else",
        "propertyNames",
        "unevaluatedItems",
        "unevaluatedProperties",
        "contentSchema",
    }
)
_SUBSCHEMA_SEQUENCE_KEYS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_SUBSCHEMA_MAPPING_KEYS = frozenset({"properties", "patternProperties", "dependentSchemas"})
_VERBATIM_KEYS = frozenset(
    {
        "title",
        "description",
        "default",
        "examples",
        "example",
        "enum",
        "const",
        "required",
        "multipleOf",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
        "maxLength",
        "minLength",
        "pattern",
        "maxItems",
        "minItems",
        "uniqueItems",
        "maxContains",
        "minContains",
        "maxProperties",
        "minProperties",
        "dependentRequired",
        "contentEncoding",
        "contentMediaType",
        "deprecated",
        "readOnly",
        "writeOnly",
    }
)
_SUPPORTED_KEYS = (
    _SUBSCHEMA_KEYS
    | _SUBSCHEMA_SEQUENCE_KEYS
    | _SUBSCHEMA_MAPPING_KEYS
    | _VERBATIM_KEYS
    | {"additionalProperties", "type", "format", "discriminator"}
)


def _openapi_type(value: str) -> OpenAPIType:
    try:
        return OpenAPIType(value)
    except ValueError as exc:
        raise SchemaConversionError(f"Unsupported JSON schema type {value!r} in a library-generated schema") from exc


def _openapi_format(value: str) -> OpenAPIFormat | str:
    try:
        return OpenAPIFormat(value)
    except ValueError:
        return value


def _discriminator(value: Mapping[str, Any], lookup_ref: _RefResolver) -> Discriminator:
    targets = {name: lookup_ref(ref) for name, ref in value.get("mapping", {}).items()}
    mapping = {name: target.ref for name, target in targets.items() if isinstance(target, Reference)}
    return Discriminator(property_name=value["propertyName"], mapping=mapping or None)


def _convert_value(key: str, value: Any, lookup_ref: _RefResolver, dropped: set[str]) -> Any:
    if key in _SUBSCHEMA_KEYS:
        return json_schema_to_spec(value, lookup_ref, dropped)
    if key in _SUBSCHEMA_SEQUENCE_KEYS:
        return [json_schema_to_spec(item, lookup_ref, dropped) for item in value]
    if key in _SUBSCHEMA_MAPPING_KEYS:
        return {name: json_schema_to_spec(item, lookup_ref, dropped) for name, item in value.items()}
    if key == "additionalProperties":
        return value if isinstance(value, bool) else json_schema_to_spec(value, lookup_ref, dropped)
    if key == "type":
        return [_openapi_type(item) for item in value] if isinstance(value, list) else _openapi_type(value)
    if key == "format":
        return _openapi_format(value)
    if key == "discriminator":
        return _discriminator(value, lookup_ref)
    return value


def _is_redundant(key: str, value: Any, schema: Mapping[str, Any]) -> bool:
    return (
        key == "items"
        and value is False
        and "prefixItems" in schema
        and schema.get("maxItems") == len(schema["prefixItems"])
    )


def _nullable_embedded_scalar(value: Mapping[str, Any], kwargs: dict[str, Any]) -> Schema | None:
    members = value.get("anyOf")
    if value.keys() & {"$ref", "type"} or not (
        isinstance(members, list) and len(members) == 2 and {"type": "null"} in members
    ):
        return None
    index = 1 - members.index({"type": "null"})
    member = members[index]
    if not (isinstance(member, dict) and member.keys() == {"$ref"} and member["$ref"].startswith(EMBED_PREFIX)):
        return None
    rest = {key: item for key, item in kwargs.items() if key != "any_of"}
    return nullable_scalar(kwargs["any_of"][index], **rest)


def json_schema_to_spec(
    value: Mapping[str, Any] | bool, lookup_ref: _RefResolver, dropped: set[str] | None = None
) -> Schema | Reference:
    """Convert a JSON schema to an OpenAPI schema.

    A ``$ref`` with sibling keys becomes the target with those keys if they only add annotations the target lacks,
    else an ``allOf`` with the target first. Keys OpenAPI cannot represent are left out.

    Args:
        value: The JSON schema.
        lookup_ref: Maps each ``$ref`` value to the schema or reference it stands for.
        dropped: Collects the keys left out.

    Returns:
        The OpenAPI schema, or the result of ``lookup_ref`` for a schema that is only a ``$ref``.

    Raises:
        SchemaConversionError: If the JSON schema has a type OpenAPI does not know.
    """
    if dropped is None:
        dropped = set()
    if isinstance(value, bool):
        return Schema() if value else Schema(schema_not=Schema())
    if value.keys() == {"$ref"}:
        return lookup_ref(value["$ref"])

    dropped.update(key for key in value if key != "$ref" and key not in _SUPPORTED_KEYS)
    kwargs: dict[str, Any] = {
        _ATTRIBUTES.get(key, key): _convert_value(key, item, lookup_ref, dropped)
        for key, item in value.items()
        if key in _SUPPORTED_KEYS and not _is_redundant(key, item, value)
    }
    if "$ref" in value:
        target = lookup_ref(value["$ref"])
        if isinstance(target, Schema) and all(key in _ANNOTATIONS and getattr(target, key) is None for key in kwargs):
            return replace(target, **kwargs)
        kwargs["all_of"] = [target, *kwargs.get("all_of", ())]
    return _nullable_embedded_scalar(value, kwargs) or Schema(**kwargs)
