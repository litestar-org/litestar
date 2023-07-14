from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Collection, Generic, TypeVar

from pydantic import BaseModel

from litestar.dto.factory.base import AbstractDTOFactory
from litestar.dto.factory.data_structures import DTOFieldDefinition
from litestar.dto.factory.field import DTO_FIELD_META_KEY, DTOField
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator

    from pydantic.fields import ModelField

    from litestar.typing import FieldDefinition

__all__ = ("PydanticDTO",)

T = TypeVar("T", bound="BaseModel | Collection[BaseModel]")


def _determine_default(field_definition: FieldDefinition, model_field: ModelField) -> Any:
    if (
        model_field.default is Ellipsis
        or model_field.default_factory is not None
        or (model_field.default is None and not field_definition.is_optional)
    ):
        return Empty

    return model_field.default


class PydanticDTO(AbstractDTOFactory[T], Generic[T]):
    """Support for domain modelling with Pydantic."""

    __slots__ = ()

    model_type: ClassVar[type[BaseModel]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[BaseModel]) -> Generator[DTOFieldDefinition, None, None]:
        model_field_definitions = get_model_type_hints(model_type)
        for key, model_field in model_type.__fields__.items():
            field_definition = model_field_definitions[key]
            model_field = model_type.__fields__[key]
            dto_field = (field_definition.extra or {}).pop(DTO_FIELD_META_KEY, DTOField())

            yield replace(
                DTOFieldDefinition.from_field_definition(
                    field_definition=field_definition,
                    dto_field=dto_field,
                    unique_model_name=get_fully_qualified_class_name(model_type),
                    default_factory=model_field.default_factory or Empty,
                    dto_for=None,
                ),
                default=_determine_default(field_definition, model_field),
                name=key,
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(BaseModel)
