from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, Any, Mapping

from litestar.utils.helpers import get_name

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.openapi.spec import Example
    from litestar.typing import FieldDefinition

__all__ = (
    "_type_or_first_not_none_inner_type",
    "_should_create_enum_schema",
    "_should_create_literal_schema",
    "_get_normalized_schema_key",
)


def _type_or_first_not_none_inner_type(field_definition: FieldDefinition) -> Any:
    """Get the first inner type that is not None.

    This is a narrow focussed utility to be used when we know that a field definition either represents
    a single type, or a single type in a union with `None`, and we want the single type.

    Args:
        field_definition: A field definition instance.

    Returns:
        A field definition instance.
    """
    if not field_definition.is_optional:
        return field_definition.annotation
    inner = next((t for t in field_definition.inner_types if not t.is_none_type), None)
    if inner is None:
        raise ValueError("Field definition has no inner type that is not None")
    return inner.annotation


def _should_create_enum_schema(field_definition: FieldDefinition) -> bool:
    """Predicate to determine if we should create an enum schema for the field def, or not.

    This returns true if the field definition is an enum, or if the field definition is a union
    of an enum and ``None``.

    When an annotation is ``SomeEnum | None`` we should create a schema for the enum that includes ``null``
    in the enum values.

    Args:
        field_definition: A field definition instance.

    Returns:
        A boolean
    """
    return field_definition.is_subclass_of(Enum) or (
        field_definition.is_optional
        and len(field_definition.args) == 2
        and field_definition.has_inner_subclass_of(Enum)
    )


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
    return (
        field_definition.is_literal
        or field_definition.is_optional
        and all(inner.is_literal for inner in field_definition.inner_types if not inner.is_none_type)
    )


TYPE_NAME_NORMALIZATION_SUB_REGEX = re.compile(r"[^a-zA-Z0-9]+")
TYPE_NAME_EXTRACTION_REGEX = re.compile(r"<\w+ '(.+)'")


def _replace_non_alphanumeric_match(match: re.Match) -> str:
    # we don't want to introduce leading or trailing underscores, so we only replace a
    # char with an underscore if we're not at the beginning or at the end of the
    # matchable string
    if match.start() == 0 or match.end() == match.endpos:
        return ""
    return "_"


def _get_normalized_schema_key(type_annotation_str: str) -> str:
    """Normalize a type annotation, replacing all non-alphanumeric with underscores.
    Existing underscores will be left as-is

    Args:
        type_annotation_str: A string representing a type annotation
            (i.e. 'typing.Dict[str, typing.Any]' or '<class 'model.Foo'>')

    Returns:
        A normalized version of the input string
    """
    # extract names from repr() style annotations like <class 'foo.bar.Baz'>
    normalized_name = TYPE_NAME_EXTRACTION_REGEX.sub(r"\g<1>", type_annotation_str)
    # replace all non-alphanumeric characters with underscores, ensuring no leading or
    # trailing underscores
    return TYPE_NAME_NORMALIZATION_SUB_REGEX.sub(_replace_non_alphanumeric_match, normalized_name)


def get_formatted_examples(field_definition: FieldDefinition, examples: Sequence[Example]) -> Mapping[str, Example]:
    """Format the examples into the OpenAPI schema format."""

    name = field_definition.name or get_name(field_definition.type_)
    name = name.lower()

    return {f"{name}-example-{i}": example for i, example in enumerate(examples, 1)}
