from __future__ import annotations

from typing import TYPE_CHECKING, NewType, TypeVar

from msgspec import Struct, defstruct, field

from litestar.dto.factory._backends.utils import create_transfer_model_type_annotation
from litestar.types import Empty

if TYPE_CHECKING:
    from typing import Any

    from litestar.dto.factory._backends.types import FieldDefinitionsType


MsgspecField = NewType("MsgspecField", type)
StructT = TypeVar("StructT", bound=Struct)
T = TypeVar("T")


def _create_msgspec_field(default: Any, default_factory: Any) -> MsgspecField | None:
    kws: dict[str, Any] = {}
    if default is not Empty:
        kws["default"] = default

    if default_factory is not None:
        kws["default_factory"] = default_factory

    if not kws:
        return None

    return field(**kws)  # type:ignore[no-any-return]


def _create_struct_field_def(
    name: str, type_: type[Any], field_: MsgspecField | None
) -> tuple[str, type[Any]] | tuple[str, type[Any], MsgspecField]:
    if field_ is None:
        return name, type_
    return name, type_, field_


def _create_struct_for_field_definitions(model_name: str, field_definitions: FieldDefinitionsType) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, MsgspecField]] = []
    for field_def in field_definitions:
        field_name = field_def.serialization_name or field_def.name

        if field_def.computed_field_info:
            for parsed_param in field_def.computed_field_info.parsed_signature.parameters.values():
                struct_fields.append(
                    _create_struct_field_def(
                        parsed_param.name, parsed_param.annotation, _create_msgspec_field(parsed_param.default, None)
                    )
                )
            continue

        struct_fields.append(
            _create_struct_field_def(
                field_name,
                create_transfer_model_type_annotation(field_def.transfer_type),
                _create_msgspec_field(field_def.default, field_def.default_factory),
            )
        )
    return defstruct(model_name, struct_fields, frozen=True, kw_only=True)
