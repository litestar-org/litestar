from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec

from litestar.openapi.spec.example import Example
from litestar.params import KwargDefinition

if TYPE_CHECKING:
    from litestar.typing import FieldDefinition


def get_meta_from_field_definition(field_definition: FieldDefinition) -> msgspec.Meta:
    return next((item for item in field_definition.metadata if isinstance(item, msgspec.Meta)), None)


def create_kwarg_definition_for_meta(meta: msgspec.Meta) -> KwargDefinition:
    return KwargDefinition(
        gt=meta.gt,
        ge=meta.ge,
        lt=meta.lt,
        le=meta.le,
        multiple_of=meta.multiple_of,
        pattern=meta.pattern,
        min_length=meta.min_length,
        max_length=meta.max_length,
        title=meta.title,
        description=meta.description,
        examples=[Example(value=e) for e in meta.examples] if meta.examples else None,
    )
