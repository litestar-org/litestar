from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Collection, Generic, TypeVar, cast

from msgspec import NODEFAULT, Struct, inspect

from litestar.dto._utils import get_model_type_hints
from litestar.dto.base_factory import AbstractDTOFactory
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.dto.field import DTO_FIELD_META_KEY, DTOField
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator

    from litestar.typing import FieldDefinition


__all__ = ("MsgspecDTO",)

T = TypeVar("T", bound="Struct | Collection[Struct]")


class MsgspecDTO(AbstractDTOFactory[T], Generic[T]):
    """Support for domain modelling with Msgspec."""

    __slots__ = ()

    model_type: ClassVar[type[Struct]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[Struct]) -> Generator[DTOFieldDefinition, None, None]:
        msgspec_fields = {f.name: f for f in cast("inspect.StructType", inspect.type_info(model_type)).fields}

        def default_or_empty(value: Any) -> Any:
            return Empty if value is NODEFAULT else value

        for key, field_definition in get_model_type_hints(model_type).items():
            msgspec_field = msgspec_fields[key]
            dto_field = (field_definition.extra or {}).pop(DTO_FIELD_META_KEY, DTOField())

            yield replace(
                DTOFieldDefinition.from_field_definition(
                    field_definition=field_definition,
                    dto_field=dto_field,
                    unique_model_name=get_fully_qualified_class_name(model_type),
                    default_factory=default_or_empty(msgspec_field.default_factory),
                    dto_for=None,
                ),
                default=default_or_empty(msgspec_field.default),
                name=key,
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(Struct)
