from __future__ import annotations

import dataclasses
from dataclasses import replace
from typing import TYPE_CHECKING, Generic, Literal, TypeVar

import msgspec.inspect
from msgspec import NODEFAULT, Struct, structs

from litestar.dto.base_dto import AbstractDTO
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.dto.field import DTO_FIELD_META_KEY, DTOField, extract_dto_field
from litestar.plugins.core._msgspec import kwarg_definition_from_field
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from collections.abc import Collection, Generator
    from typing import Any


__all__ = ("MsgspecDTO",)

T = TypeVar("T", bound="Struct | Collection[Struct]")


def _default_or_empty(value: Any) -> Any:
    return Empty if value is NODEFAULT else value


def _default_or_none(value: Any) -> Any:
    return None if value is NODEFAULT else value


def _msgspec_attribute_accessor(obj: object, name: str) -> Any:
    """Like ``getattr``, but also resolves the synthetic tag field on msgspec Structs.

    The tag field (e.g. ``"type"``) is not a real instance attribute — msgspec injects it
    only during encoding.  This accessor falls back to the struct's type-info when the
    normal attribute lookup fails so the DTO transfer layer can read the tag value.
    """
    try:
        return getattr(obj, name)
    except AttributeError:
        if isinstance(obj, Struct):
            type_info = msgspec.inspect.type_info(type(obj))  # type: ignore[arg-type]
            if name == type_info.tag_field:
                return type_info.tag
        raise


class MsgspecDTO(AbstractDTO[T], Generic[T]):
    """Support for domain modelling with Msgspec."""

    attribute_accessor = _msgspec_attribute_accessor

    @classmethod
    def generate_field_definitions(cls, model_type: type[Struct]) -> Generator[DTOFieldDefinition, None, None]:
        msgspec_fields = {f.name: f for f in structs.fields(model_type)}

        struct_info = msgspec.inspect.type_info(model_type)  # type: ignore[arg-type]
        inspect_fields: dict[str, msgspec.inspect.Field] = {
            field.name: field
            for field in struct_info.fields  # type: ignore[attr-defined]
        }

        property_fields = cls.get_property_fields(model_type)

        for key, field_definition in cls.get_model_type_hints(model_type).items():
            if key not in inspect_fields:
                continue
            kwarg_definition, extra = kwarg_definition_from_field(inspect_fields[key])
            field_definition = dataclasses.replace(field_definition, kwarg_definition=kwarg_definition)
            field_definition.extra.update(extra)
            dto_field = extract_dto_field(field_definition, field_definition.extra)
            field_definition.extra.pop(DTO_FIELD_META_KEY, None)
            msgspec_field = msgspec_fields[key]

            yield replace(
                DTOFieldDefinition.from_field_definition(
                    field_definition=field_definition,
                    dto_field=dto_field,
                    model_name=model_type.__name__,
                    default_factory=_default_or_none(msgspec_field.default_factory),
                ),
                default=_default_or_empty(msgspec_field.default),
                name=key,
            )

        if struct_info.tag is not None:  # type: ignore[attr-defined]
            tag_value = struct_info.tag  # type: ignore[attr-defined]
            tag_field_name = struct_info.tag_field  # type: ignore[attr-defined]
            tag_annotation = Literal[tag_value]  # type: ignore[valid-type]
            yield replace(
                DTOFieldDefinition.from_field_definition(
                    field_definition=FieldDefinition.from_annotation(tag_annotation, name=tag_field_name),
                    dto_field=DTOField(mark="read-only"),
                    model_name=model_type.__name__,
                    default_factory=None,
                ),
                default=tag_value,
                name=tag_field_name,
            )

        for key, property_field in property_fields.items():
            if key.startswith("_"):
                continue

            yield DTOFieldDefinition.from_field_definition(
                property_field,
                model_name=model_type.__name__,
                default_factory=None,
                dto_field=DTOField(mark="read-only"),
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(Struct)
