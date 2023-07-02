from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Collection, Generic, TypeVar

from pydantic import BaseModel

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.data_structures import FieldDefinition
from litestar.dto.factory.field import DTO_FIELD_META_KEY, DTOField
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator

    from pydantic.fields import ModelField

    from litestar.typing import ParsedType

__all__ = ("PydanticDTO",)

T = TypeVar("T", bound="BaseModel | Collection[BaseModel]")


def _determine_default(parsed_type: ParsedType, model_field: ModelField) -> Any:
    if (
        model_field.default is Ellipsis
        or model_field.default_factory is not None
        or (model_field.default is None and not parsed_type.is_optional)
    ):
        return Empty

    return model_field.default


class PydanticDTO(AbstractDTOFactory[T], Generic[T]):
    """Support for domain modelling with Pydantic."""

    __slots__ = ()

    model_type: ClassVar[type[BaseModel]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[BaseModel]) -> Generator[FieldDefinition, None, None]:
        model_parsed_types = get_model_type_hints(model_type)
        for key, model_field in model_type.__fields__.items():
            parsed_type = model_parsed_types[key]
            model_field = model_type.__fields__[key]
            dto_field = (parsed_type.extra or {}).pop(DTO_FIELD_META_KEY, DTOField())

            yield replace(
                FieldDefinition.from_parsed_type(
                    parsed_type=parsed_type,
                    dto_field=dto_field,
                    unique_model_name=get_fully_qualified_class_name(model_type),
                    default_factory=model_field.default_factory or Empty,
                    dto_for=None,
                ),
                default=_determine_default(parsed_type, model_field),
                name=key,
            )

    @classmethod
    def detect_nested_field(cls, parsed_type: ParsedType) -> bool:
        return parsed_type.is_subclass_of(BaseModel)
