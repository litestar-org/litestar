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


def kwarg_definition_from_field(field: msgspec.inspect.Field) -> tuple[ParameterKwarg | None, dict[str, Any]]:
    extra: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}
    if isinstance(field.type, msgspec.inspect.Metadata):
        meta = field.type
        field_type = meta.type
        if extra_json_schema := meta.extra_json_schema:
            kwargs["title"] = extra_json_schema.get("title")
            kwargs["description"] = extra_json_schema.get("description")
            if examples := extra_json_schema.get("examples"):
                kwargs["examples"] = [Example(value=e) for e in examples]
            kwargs["schema_extra"] = extra_json_schema.get("extra")
        extra = meta.extra or {}
    else:
        field_type = field.type

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

    parameter_defaults = {
        f.name: default for f in dataclasses.fields(ParameterKwarg) if (default := f.default) is not dataclasses.MISSING
    }
    kwargs_without_defaults = {k: v for k, v in kwargs.items() if v != parameter_defaults[k]}

    if kwargs_without_defaults:
        return ParameterKwarg(**kwargs_without_defaults), extra
    return None, extra
