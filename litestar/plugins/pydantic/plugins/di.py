from __future__ import annotations

import inspect
from inspect import Signature
from typing import Any

from typing_extensions import Annotated

from litestar.di import NamedDependency
from litestar.params import ParameterKwarg
from litestar.plugins import DIPlugin
from litestar.plugins.pydantic.utils import is_pydantic_model_class
from litestar.utils.typing import unwrap_annotation


def _resolve_field_annotation(type_: Any, field_name: str) -> Any:
    # pydantic v2: model_fields[name] is FieldInfo with `.annotation` (base type) and `.metadata` list
    model_fields = getattr(type_, "model_fields", None)
    if model_fields is not None:
        field_info = model_fields[field_name]
        annotation = getattr(field_info, "annotation", None)
        metadata = getattr(field_info, "metadata", None) or []
        if annotation is None:
            return Any
        if metadata:
            return Annotated[(annotation, *metadata)]
        return annotation
    # pydantic v1: __fields__[name] is ModelField with `.annotation`
    fields = getattr(type_, "__fields__", None)
    if fields is not None and field_name in fields:
        field = fields[field_name]
        annotation = getattr(field, "annotation", None)
        if annotation is not None:
            return annotation
    return Any


def _maybe_wrap_in_named_dependency(ann: Any) -> Any:
    metadata = unwrap_annotation(ann)[1]
    if not any(isinstance(m, ParameterKwarg) for m in metadata):
        return NamedDependency[ann]  # type: ignore[misc]
    return ann


class PydanticDIPlugin(DIPlugin):
    def has_typed_init(self, type_: Any) -> bool:
        return is_pydantic_model_class(type_)

    def get_typed_init(self, type_: Any) -> tuple[Signature, dict[str, Any]]:
        try:
            model_fields = dict(type_.model_fields)
        except AttributeError:
            model_fields = {k: model_field.field_info for k, model_field in type_.__fields__.items()}

        type_hints = {field_name: _resolve_field_annotation(type_, field_name) for field_name in model_fields}
        parameters = [
            inspect.Parameter(
                name=field_name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=_maybe_wrap_in_named_dependency(type_hints[field_name]),
            )
            for field_name in model_fields
        ]
        return Signature(parameters), type_hints
