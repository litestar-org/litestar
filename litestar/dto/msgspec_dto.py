from __future__ import annotations

from contextlib import suppress
from dataclasses import replace
from typing import TYPE_CHECKING, Generic, TypeVar

import msgspec.inspect
from msgspec import NODEFAULT, Struct, structs

from litestar.dto._msgspec_rejection import CONSTRAINT_HINT, contains_meta, rejected_field_message
from litestar.dto.base_dto import AbstractDTO
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.dto.field import DTO_FIELD_META_KEY, DTOField, extract_dto_field
from litestar.exceptions.dto_exceptions import InvalidAnnotationException
from litestar.plugins.core._msgspec import kwarg_definition_from_field
from litestar.types.empty import Empty

if TYPE_CHECKING:
    from collections.abc import Collection, Generator
    from typing import Any

    from litestar.typing import FieldDefinition


__all__ = ("MsgspecDTO",)

T = TypeVar("T", bound="Struct | Collection[Struct]")


def _default_or_empty(value: Any) -> Any:
    return Empty if value is NODEFAULT else value


def _default_or_none(value: Any) -> Any:
    return None if value is NODEFAULT else value


def _rejected_field_message(
    model_type: type[Struct], field_names: Collection[str], dto_type: type[MsgspecDTO]
) -> str | None:
    type_hints = dto_type.get_model_type_hints(model_type)
    for name in field_names:
        field_definition = type_hints[name]
        try:
            msgspec.inspect.type_info(field_definition.raw)
        except TypeError as field_exc:
            return rejected_field_message(
                "msgspec cannot inspect",
                model_type,
                field_definition,
                field_exc,
                hint=CONSTRAINT_HINT if contains_meta(field_definition) else None,
            )
    return None


class MsgspecDTO(AbstractDTO[T], Generic[T]):
    """Support for domain modelling with Msgspec."""

    @classmethod
    def generate_field_definitions(cls, model_type: type[Struct]) -> Generator[DTOFieldDefinition, None, None]:
        msgspec_fields = {f.name: f for f in structs.fields(model_type)}

        try:
            struct_info = msgspec.inspect.type_info(model_type)
        except TypeError as exc:
            message = None
            with suppress(Exception):
                message = _rejected_field_message(model_type, msgspec_fields, cls)
            raise InvalidAnnotationException(
                message or f"msgspec cannot inspect {model_type.__name__!r}: {exc}"
            ) from exc

        inspect_fields: dict[str, msgspec.inspect.Field] = {
            field.name: field
            for field in struct_info.fields  # type: ignore[attr-defined]
        }

        property_fields = cls.get_property_fields(model_type)

        for key, field_definition in cls.get_model_type_hints(model_type).items():
            if key not in inspect_fields:
                continue
            _, extra = kwarg_definition_from_field(inspect_fields[key])
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
