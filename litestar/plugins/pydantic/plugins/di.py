from __future__ import annotations

import inspect
from inspect import Signature
from typing import Annotated, Any

from pydantic_core import PydanticUndefined

from litestar.di import NamedDependency
from litestar.plugins import DIPlugin
from litestar.plugins.pydantic.utils import is_pydantic_model_class
from litestar.typing import FieldDefinition


def _resolve_field_annotation(field_info: Any) -> Any:
    # model_fields[name] is FieldInfo with `.annotation` (base type) and `.metadata` list
    annotation = getattr(field_info, "annotation", None)
    metadata = getattr(field_info, "metadata", None) or []
    if annotation is None:
        return Any
    if metadata:
        return Annotated[(annotation, *metadata)]
    return annotation


def _maybe_wrap_in_named_dependency(ann: Any) -> Any:
    if not FieldDefinition.from_annotation(ann).is_marker_field:
        return NamedDependency[ann]  # type: ignore[misc]
    return ann


class PydanticDIPlugin(DIPlugin):
    def has_typed_init(self, type_: Any) -> bool:
        return is_pydantic_model_class(type_)

    def get_typed_init(self, type_: Any) -> tuple[Signature, dict[str, Any]]:
        model_fields = dict(type_.model_fields)
        type_hints = {
            field_name: _maybe_wrap_in_named_dependency(_resolve_field_annotation(field_info))
            for field_name, field_info in model_fields.items()
        }
        parameters = [
            inspect.Parameter(
                name=field_name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=type_hints[field_name],
                default=inspect.Parameter.empty if field_info.default is PydanticUndefined else field_info.default,
            )
            for field_name, field_info in model_fields.items()
        ]
        return Signature(parameters), type_hints
