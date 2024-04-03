from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Generic, TypeVar

from msgspec import NODEFAULT, Struct, structs

from litestar.dto.base_dto import AbstractDTO
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.dto.field import DTO_FIELD_META_KEY, DTOField
from litestar.params import KwargDefinition
from litestar.types.empty import Empty
from litestar.utils.msgspec import create_kwarg_definition_for_meta, get_meta_from_field_definition

if TYPE_CHECKING:
    from typing import Any, Collection, Generator

    from litestar.typing import FieldDefinition


__all__ = ("MsgspecDTO",)

T = TypeVar("T", bound="Struct | Collection[Struct]")


class MsgspecDTO(AbstractDTO[T], Generic[T]):
    """Support for domain modelling with Msgspec."""

    @classmethod
    def generate_field_definitions(cls, model_type: type[Struct]) -> Generator[DTOFieldDefinition, None, None]:
        msgspec_fields = {f.name: f for f in structs.fields(model_type)}

        def default_or_empty(value: Any) -> Any:
            return Empty if value is NODEFAULT else value

        def default_or_none(value: Any) -> Any:
            return None if value is NODEFAULT else value

        for key, field_definition in cls.get_model_type_hints(model_type).items():
            msgspec_field = msgspec_fields[key]

            kwarg_definition: KwargDefinition | None
            dto_field: DTOField
            if meta := get_meta_from_field_definition(field_definition):
                dto_field = (meta.extra or {}).pop(DTO_FIELD_META_KEY, DTOField())
                kwarg_definition = create_kwarg_definition_for_meta(meta)
            else:
                dto_field = DTOField()
                kwarg_definition = None

            yield replace(
                DTOFieldDefinition.from_field_definition(
                    field_definition=field_definition,
                    dto_field=dto_field,
                    model_name=model_type.__name__,
                    default_factory=default_or_none(msgspec_field.default_factory),
                ),
                default=default_or_empty(msgspec_field.default),
                name=key,
                kwarg_definition=kwarg_definition,
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(Struct)
