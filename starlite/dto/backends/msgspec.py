from __future__ import annotations

from typing import TYPE_CHECKING, NewType
from uuid import uuid4

from msgspec import Struct, defstruct, field

from starlite.dto.types import NestedFieldDefinition
from starlite.enums import MediaType
from starlite.exceptions import SerializationException
from starlite.serialization import decode_json, decode_msgpack
from starlite.types import Empty

from .abc import AbstractDTOBackend

if TYPE_CHECKING:
    from typing import Any, Iterable

    from starlite.dto.types import FieldDefinition, FieldDefinitionsType

__all__ = ["MsgspecDTOBackend"]


MsgspecField = NewType("MsgspecField", type)


class MsgspecDTOBackend(AbstractDTOBackend[Struct]):
    def parse_raw(self, raw: bytes, media_type: MediaType | str) -> Struct | Iterable[Struct]:
        if media_type == MediaType.JSON:
            transfer_data = decode_json(raw, type_=self.annotation)
        elif media_type == MediaType.MESSAGEPACK:
            transfer_data = decode_msgpack(raw, type_=self.annotation)
        else:
            raise SerializationException(f"Unsupported media type: '{media_type}'")
        return transfer_data  # type:ignore[return-value]

    @classmethod
    def from_field_definitions(cls, annotation: Any, field_definitions: FieldDefinitionsType) -> Any:
        return cls(annotation, _create_msgspec_struct_for_field_definitions(str(uuid4()), field_definitions))


def _create_msgspec_field(field_definition: FieldDefinition) -> MsgspecField | None:
    kws: dict[str, Any] = {}
    if field_definition.default is not Empty:
        kws["default"] = field_definition.default

    if field_definition.default_factory is not Empty:
        kws["default_factory"] = field_definition.default_factory

    if not kws:
        return None

    return field(**kws)  # type:ignore[no-any-return]


def _create_struct_field_def(
    name: str, type_: type[Any], field_: MsgspecField | None
) -> tuple[str, type[Any]] | tuple[str, type[Any], MsgspecField]:
    if field_ is None:
        return name, type_
    return name, type_, field_


def _create_msgspec_struct_for_field_definitions(
    model_name: str, field_definitions: FieldDefinitionsType
) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, MsgspecField]] = []
    for k, v in field_definitions.items():
        if isinstance(v, NestedFieldDefinition):
            nested_struct = _create_msgspec_struct_for_field_definitions(
                f"{model_name}.{k}", v.nested_field_definitions
            )
            struct_fields.append(
                _create_struct_field_def(k, v.make_field_type(nested_struct), _create_msgspec_field(v.field_definition))
            )
        else:
            struct_fields.append(_create_struct_field_def(k, v.field_type, _create_msgspec_field(v)))
    return defstruct(model_name, struct_fields, frozen=True, kw_only=True)
