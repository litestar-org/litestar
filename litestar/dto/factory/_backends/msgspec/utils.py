from __future__ import annotations

from typing import TYPE_CHECKING, NewType, TypeVar, Union

from msgspec import UNSET, Struct, UnsetType, defstruct, field

from litestar.dto.factory._backends.utils import create_transfer_model_type_annotation
from litestar.types import Empty

if TYPE_CHECKING:
    from typing import Any

    from litestar.dto.factory._backends.types import FieldDefinitionsType, TransferFieldDefinition


MsgspecField = NewType("MsgspecField", type)
StructT = TypeVar("StructT", bound=Struct)
T = TypeVar("T")


def _create_msgspec_field(field_definition: TransferFieldDefinition) -> MsgspecField:
    kws: dict[str, Any] = {}
    if field_definition.is_partial:
        kws["default"] = UNSET

    elif field_definition.default is not Empty:
        kws["default"] = field_definition.default

    elif field_definition.default_factory is not None:
        kws["default_factory"] = field_definition.default_factory

    return field(**kws)  # type:ignore[no-any-return]


def _create_struct_for_field_definitions(model_name: str, field_definitions: FieldDefinitionsType) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, MsgspecField]] = []
    for field_def in field_definitions:
        if field_def.is_excluded:
            continue

        field_name = field_def.serialization_name or field_def.name

        field_type = create_transfer_model_type_annotation(field_def.transfer_type)
        if field_def.is_partial:
            field_type = Union[field_type, UnsetType]

        struct_fields.append((field_name, field_type, _create_msgspec_field(field_def)))
    return defstruct(model_name, struct_fields, frozen=True, kw_only=True)
