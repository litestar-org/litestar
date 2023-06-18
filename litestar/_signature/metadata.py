from __future__ import annotations

from typing import Any, TypeVar, cast

from litestar.openapi.spec import Example
from litestar.params import KwargDefinition
from litestar.utils import is_non_string_sequence

T = TypeVar("T", bound=KwargDefinition)


def _parse_metadata(value: Any, is_sequence_container: bool) -> dict[str, Any]:
    """Parse metadata from a value.

    Args:
        value: A metadata value from annotation, namely anything stored under Annotated[x, metadata...]
        is_sequence_container: Whether the type is a sequence container (list, tuple etc...)

    Returns:
        A dictionary of constraints, which fulfill the kwargs of a KwargDefinition class.
    """
    extra = cast("dict[str, Any] | None", getattr(value, "extra", None))
    if extra and (example := extra.get("example")):
        example_list = [Example(value=example)]
    elif examples := getattr(value, "examples", None):
        example_list = [Example(value=example) for example in cast("list[str]", examples)]
    else:
        example_list = None

    return {
        k: v
        for k, v in {
            "gt": getattr(value, "gt", None),
            "ge": getattr(value, "ge", None),
            "lt": getattr(value, "lt", None),
            "le": getattr(value, "le", None),
            "multiple_of": getattr(value, "multiple_of", None),
            "min_length": getattr(value, "min_length", None) if not is_sequence_container else None,
            "max_length": getattr(value, "max_length", None) if not is_sequence_container else None,
            "description": getattr(value, "description", None),
            "examples": example_list,
            "title": getattr(value, "title", None),
            "lower_case": getattr(value, "to_lower", None),
            "upper_case": getattr(value, "to_upper", None),
            "pattern": getattr(value, "regex", getattr(value, "pattern", None)),
            "min_items": getattr(value, "min_items", getattr(value, "min_length", None))
            if is_sequence_container
            else None,
            "max_items": getattr(value, "max_items", getattr(value, "max_length", None))
            if is_sequence_container
            else None,
            "const": getattr(value, "const", None) is not None,
        }.items()
        if v is not None
    }


def _create_metadata_from_type(metadata: list[Any], model: type[T], field_type: Any) -> T | None:
    is_sequence_container = is_non_string_sequence(field_type)
    constraints: dict[str, Any] = {}
    for value in metadata:
        constraints.update(_parse_metadata(value=value, is_sequence_container=is_sequence_container))
    return model(**constraints) if constraints else None
