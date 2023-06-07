from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast

from msgspec import NODEFAULT, Struct, inspect

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.data_structures import FieldDefinition
from litestar.dto.factory.field import DTO_FIELD_META_KEY, DTOField
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import Any, ClassVar, Collection, Generator

    from litestar.typing import ParsedType

__all__ = ("MsgspecDTO",)

T = TypeVar("T", bound="Struct | Collection[Struct]")


class MsgspecDTO(AbstractDTOFactory[T], Generic[T]):
    """Support for domain modelling with Msgspec."""

    __slots__ = ()

    model_type: ClassVar[type[Struct]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[Struct]) -> Generator[FieldDefinition, None, None]:
        msgspec_fields = {f.name: f for f in cast("inspect.StructType", inspect.type_info(model_type)).fields}

        def default_or_empty(value: Any) -> Any:
            if value is NODEFAULT:
                return Empty
            return value

        for key, parsed_type in get_model_type_hints(model_type).items():
            msgspec_field = msgspec_fields[key]

            if isinstance(msgspec_field.type, inspect.Metadata):
                dto_field = (msgspec_field.type.extra or {}).get(DTO_FIELD_META_KEY, DTOField())
            else:
                dto_field = DTOField()

            field_def = FieldDefinition(
                name=key,
                default=default_or_empty(msgspec_field.default),
                parsed_type=parsed_type,
                default_factory=default_or_empty(msgspec_field.default_factory),
                dto_field=dto_field,
                unique_model_name=get_fully_qualified_class_name(model_type),
                dto_for=None,
            )

            yield field_def

    @classmethod
    def detect_nested_field(cls, parsed_type: ParsedType) -> bool:
        return parsed_type.is_subclass_of(Struct)
