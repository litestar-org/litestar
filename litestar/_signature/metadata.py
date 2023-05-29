from __future__ import annotations

from typing import Any, TypeVar

from msgspec import Meta
from pydantic.fields import FieldInfo

from litestar.openapi.spec import Example
from litestar.params import KwargDefinition
from litestar.utils import is_non_string_sequence, is_pydantic_constrained_field

T = TypeVar("T", bound=KwargDefinition)


def _parse_msgspec_meta(value: Any, model: type[T], is_sequence_container: bool) -> T:
    return model(
        description=value.description,
        examples=[Example(value=example) for example in value.examples] if value.examples else None,
        ge=value.ge,
        gt=value.gt,
        le=value.le,
        lt=value.lt,
        max_items=value.max_length if is_sequence_container else None,
        max_length=value.max_length if not is_sequence_container else None,
        min_items=value.min_length if is_sequence_container else None,
        min_length=value.min_length if not is_sequence_container else None,
        multiple_of=value.multiple_of,
        pattern=value.pattern,
        title=value.title,
    )


def _parse_pydantic_fieldinfo(value: Any, model: type[T], is_sequence_container: bool) -> T | None:
    return model(
        **{
            k: v
            for k, v in {
                "gt": value.gt,
                "ge": value.ge,
                "lt": value.lt,
                "le": value.le,
                "multiple_of": value.multiple_of,
                "min_length": value.min_length if not is_sequence_container else None,
                "max_length": value.max_length if not is_sequence_container else None,
                "description": value.description,
                "examples": [Example(value=value.extra["example"])] if value.extra.get("example") else None,
                "title": value.title,
                # renamed in pydantic v2
                "pattern": getattr(value, "regex", getattr(value, "pattern", None)),
                # merged in pydantic v2
                "min_items": getattr(value, "min_items", getattr(value, "min_length", None))
                if is_sequence_container
                else None,
                "max_items": getattr(value, "max_items", getattr(value, "max_length", None))
                if is_sequence_container
                else None,
                # removed in pydantic v2
                "const": getattr(value, "const", None) is not None,
            }.items()
            if v is not None
        }
    )


def _parse_pydantic_constrained_field(value: Any, model: type[T], is_sequence_container: bool) -> T:
    return model(
        **{
            k: v
            for k, v in {
                "gt": getattr(value, "gt", None),
                "ge": getattr(value, "ge", None),
                "lt": getattr(value, "lt", None),
                "le": getattr(value, "le", None),
                "multiple_of": getattr(value, "multiple_of", None),
                "min_length": getattr(value, "min_length", None) if not is_sequence_container else None,
                "max_length": getattr(value, "max_length", None) if not is_sequence_container else None,
                "lower_case": getattr(value, "to_lower", None),
                "upper_case": getattr(value, "to_upper", None),
                "pattern": getattr(value, "regex", None),
                "min_items": getattr(value, "min_items", getattr(value, "min_length", None))
                if is_sequence_container
                else None,
                "max_items": getattr(value, "max_items", getattr(value, "max_length", None))
                if is_sequence_container
                else None,
            }.items()
            if v is not None
        }
    )


def _create_metadata_from_type(value: Any, model: type[T], field_type: Any) -> T | None:
    is_sequence_container = is_non_string_sequence(field_type)
    if isinstance(value, Meta):
        return _parse_msgspec_meta(value=value, model=model, is_sequence_container=is_sequence_container)
    if isinstance(value, FieldInfo):
        return _parse_pydantic_fieldinfo(value=value, model=model, is_sequence_container=is_sequence_container)
    if is_pydantic_constrained_field(field_type):
        return _parse_pydantic_constrained_field(value=value, model=model, is_sequence_container=is_sequence_container)

    return None  # pragma: no cover
