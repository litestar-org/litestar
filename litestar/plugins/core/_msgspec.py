from __future__ import annotations

import dataclasses
import inspect
from inspect import Signature
from typing import Any

import msgspec

from litestar.openapi.spec import Example
from litestar.params import ParameterKwarg
from litestar.plugins import DIPlugin

__all__ = ("MsgspecDIPlugin", "kwarg_definition_from_field")


class MsgspecDIPlugin(DIPlugin):
    def has_typed_init(self, type_: Any) -> bool:
        return type(type_) is type(msgspec.Struct)

    def get_typed_init(self, type_: Any) -> tuple[Signature, dict[str, Any]]:
        parameters = []
        type_hints = {}
        for field_info in msgspec.structs.fields(type_):
            type_hints[field_info.name] = field_info.type
            parameters.append(
                inspect.Parameter(
                    name=field_info.name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    annotation=field_info.type,
                    default=field_info.default,
                )
            )
        return inspect.Signature(parameters), type_hints


def _extract_type_constraints(field_type: msgspec.inspect.Type) -> dict[str, Any]:
    """Extract type-specific constraints from a field type."""
    constraints: dict[str, Any] = {}
    if isinstance(
        field_type,
        (
            msgspec.inspect.IntType,
            msgspec.inspect.FloatType,
        ),
    ):
        constraints["gt"] = field_type.gt
        constraints["ge"] = field_type.ge
        constraints["lt"] = field_type.lt
        constraints["le"] = field_type.le
        constraints["multiple_of"] = field_type.multiple_of
    elif isinstance(
        field_type,
        (
            msgspec.inspect.StrType,
            msgspec.inspect.BytesType,
            msgspec.inspect.ByteArrayType,
            msgspec.inspect.MemoryViewType,
        ),
    ):
        constraints["min_length"] = field_type.min_length
        constraints["max_length"] = field_type.max_length
        if isinstance(field_type, msgspec.inspect.StrType):
            constraints["pattern"] = field_type.pattern
    elif isinstance(
        field_type,
        (
            msgspec.inspect.ListType,
            msgspec.inspect.SetType,
            msgspec.inspect.FrozenSetType,
            msgspec.inspect.VarTupleType,
        ),
    ):
        constraints["min_items"] = field_type.min_length
        constraints["max_items"] = field_type.max_length
    return constraints


def kwarg_definition_from_field(field: msgspec.inspect.Field) -> tuple[ParameterKwarg | None, dict[str, Any]]:
    extra: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}

    # Collect all Metadata from the field type. A UnionType may contain multiple
    # Metadata members (e.g. Annotated[int, Meta()] | Annotated[str, Meta()] | None).
    metas: list[msgspec.inspect.Metadata] = []
    if isinstance(field.type, msgspec.inspect.Metadata):
        metas = [field.type]
    elif isinstance(field.type, msgspec.inspect.UnionType):
        metas = [m for m in field.type.types if isinstance(m, msgspec.inspect.Metadata)]

    if metas:
        for meta in metas:
            if extra_json_schema := meta.extra_json_schema:
                kwargs.setdefault("title", extra_json_schema.get("title"))
                kwargs.setdefault("description", extra_json_schema.get("description"))
                if examples := extra_json_schema.get("examples"):
                    existing = kwargs.get("examples", [])
                    kwargs["examples"] = existing + [Example(value=e) for e in examples]
                kwargs.setdefault("schema_extra", extra_json_schema.get("extra"))
            if meta.extra:
                extra.update(meta.extra)
            kwargs.update(_extract_type_constraints(meta.type))
    else:
        kwargs.update(_extract_type_constraints(field.type))

    parameter_defaults = {
        f.name: default for f in dataclasses.fields(ParameterKwarg) if (default := f.default) is not dataclasses.MISSING
    }
    kwargs_without_defaults = {k: v for k, v in kwargs.items() if v != parameter_defaults[k]}

    if kwargs_without_defaults:
        return ParameterKwarg(**kwargs_without_defaults), extra
    return None, extra
