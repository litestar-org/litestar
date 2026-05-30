from __future__ import annotations

import dataclasses
import inspect
from inspect import Signature
from typing import Any

import msgspec

from litestar.di import NamedDependency
from litestar.openapi.spec import Example
from litestar.params import ParameterKwarg
from litestar.plugins import DIPlugin

__all__ = ("MsgspecDIPlugin", "kwarg_definition_from_field")

from litestar.utils.typing import unwrap_annotation


class MsgspecDIPlugin(DIPlugin):
    def has_typed_init(self, type_: Any) -> bool:
        return type(type_) is type(msgspec.Struct)

    def get_typed_init(self, type_: Any) -> tuple[Signature, dict[str, Any]]:
        parameters = []
        type_hints = {}
        for field_info in msgspec.structs.fields(type_):
            metadata = unwrap_annotation(field_info.type)[1]
            type_ = field_info.type
            if not any(isinstance(m, ParameterKwarg) for m in metadata):
                type_ = NamedDependency[type_]

            type_hints[field_info.name] = type_
            parameters.append(
                inspect.Parameter(
                    name=field_info.name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    annotation=type_,
                    default=field_info.default,
                )
            )
        return inspect.Signature(parameters), type_hints


def _unwrap_optional(field_type: Any) -> Any:
    """Return the inner arm of ``Optional[X]`` so downstream isinstance checks see ``X`` directly.

    msgspec wraps it as ``UnionType((<inner>, NoneType))`` where ``<inner>`` is either a
    ``Metadata`` wrapper (for description/examples) or the bare constraint-bearing type
    (e.g. ``IntType(gt=1, ...)``) - Meta-derived constraints are hoisted onto the type.
    Heterogeneous unions are left alone.
    """
    if isinstance(field_type, msgspec.inspect.UnionType):
        non_none = [t for t in field_type.types if not isinstance(t, msgspec.inspect.NoneType)]
        if len(non_none) == 1:
            return non_none[0]
    return field_type


def kwarg_definition_from_field(field: msgspec.inspect.Field) -> tuple[ParameterKwarg | None, dict[str, Any]]:
    extra: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}
    field_type = _unwrap_optional(field.type)
    if isinstance(field_type, msgspec.inspect.Metadata):
        meta = field_type
        field_type = meta.type
        if extra_json_schema := meta.extra_json_schema:
            kwargs["title"] = extra_json_schema.get("title")
            kwargs["description"] = extra_json_schema.get("description")
            if examples := extra_json_schema.get("examples"):
                kwargs["examples"] = [Example(value=e) for e in examples]
            kwargs["schema_extra"] = extra_json_schema.get("extra")
        extra = meta.extra or {}

    if isinstance(
        field_type,
        (
            msgspec.inspect.IntType,
            msgspec.inspect.FloatType,
        ),
    ):
        kwargs["gt"] = field_type.gt
        kwargs["ge"] = field_type.ge
        kwargs["lt"] = field_type.lt
        kwargs["le"] = field_type.le
        kwargs["multiple_of"] = field_type.multiple_of
    elif isinstance(
        field_type,
        (
            msgspec.inspect.StrType,
            msgspec.inspect.BytesType,
            msgspec.inspect.ByteArrayType,
            msgspec.inspect.MemoryViewType,
        ),
    ):
        kwargs["min_length"] = field_type.min_length
        kwargs["max_length"] = field_type.max_length
        if isinstance(field_type, msgspec.inspect.StrType):
            kwargs["pattern"] = field_type.pattern
    elif isinstance(
        field_type,
        (
            msgspec.inspect.ListType,
            msgspec.inspect.SetType,
            msgspec.inspect.FrozenSetType,
            msgspec.inspect.VarTupleType,
        ),
    ):
        kwargs["min_items"] = field_type.min_length
        kwargs["max_items"] = field_type.max_length

    parameter_defaults = {
        f.name: default for f in dataclasses.fields(ParameterKwarg) if (default := f.default) is not dataclasses.MISSING
    }
    kwargs_without_defaults = {k: v for k, v in kwargs.items() if v != parameter_defaults[k]}

    if kwargs_without_defaults:
        return ParameterKwarg(**kwargs_without_defaults), extra
    return None, extra
