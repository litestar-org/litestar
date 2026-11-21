from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from litestar.openapi.spec.enums import OpenAPIType
from litestar.openapi.spec.schema import Schema
from litestar.utils.helpers import get_name

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from litestar.openapi.spec import Example, Reference
    from litestar.typing import FieldDefinition

__all__ = ("_should_create_literal_schema", "nullable_scalar")

_NULLABLE_SCALARS = frozenset({OpenAPIType.STRING, OpenAPIType.INTEGER, OpenAPIType.NUMBER, OpenAPIType.BOOLEAN})
_TYPE_DEPENDENT_KEYWORDS = (
    "one_of",
    "any_of",
    "all_of",
    "enum",
    "const",
    "schema_not",
    "schema_if",
    "then",
    "schema_else",
)


def nullable_scalar(schema: Schema | Reference, **changes: Any) -> Schema | None:
    """Make a scalar schema accept ``null`` through a ``type`` array.

    References, combinators, ``enum``, ``const`` and conditionals would also apply to ``null`` in a type array, so
    such schemas keep a ``oneOf`` with ``null`` instead.

    Args:
        schema: The schema to make nullable.
        **changes: Other attributes to set on the result.

    Returns:
        A copy of ``schema`` typed ``[<type>, null]``, or ``None`` if ``schema`` is not such a scalar.
    """
    if not (
        isinstance(schema, Schema)
        and isinstance(schema.type, OpenAPIType)
        and schema.type in _NULLABLE_SCALARS
        and all(getattr(schema, keyword) is None for keyword in _TYPE_DEPENDENT_KEYWORDS)
    ):
        return None
    return replace(schema, **changes, type=[schema.type, OpenAPIType.NULL])


def _should_create_literal_schema(field_definition: FieldDefinition) -> bool:
    """Predicate to determine if we should create a literal schema for the field def, or not.

    This returns ``True`` if the field definition is an literal, or if the field definition is a union
    of a literal and None.

    When an annotation is `Literal["anything"] | None` we should create a schema for the literal that includes `null`
    in the enum values.

    Args:
        field_definition: A field definition instance.

    Returns:
        A boolean
    """
    return field_definition.is_literal or (
        field_definition.is_optional
        and all(inner.is_literal for inner in field_definition.inner_types if not inner.is_none_type)
    )


def get_example_id(example: Example, name: str, index: int) -> str:
    """Get the example ID.

    Args:
        example: The example instance.
        name: The name of the field.
        index: The index of the example.

    Returns:
        The example ID.
    """
    return example.id or f"{name}-example-{index}"


def get_formatted_examples(field_definition: FieldDefinition, examples: Sequence[Example]) -> Mapping[str, Example]:
    """Format the examples into the OpenAPI schema format."""

    name = field_definition.name or get_name(field_definition.type_)
    name = name.lower()

    return {get_example_id(example, name, i): example for i, example in enumerate(examples, 1)}


def get_json_schema_formatted_examples(examples: Sequence[Example]) -> list[Any]:
    """Format the examples into the JSON schema format."""
    return [example.value for example in examples]
