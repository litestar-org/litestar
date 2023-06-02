from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.data_structures import FieldDefinition
from litestar.dto.factory.field import DTO_FIELD_META_KEY, DTOField
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import Any, ClassVar, Collection, Generator

    from pydantic.fields import ModelField

    from litestar.typing import ParsedType

__all__ = ("PydanticDTO",)

T = TypeVar("T", bound="BaseModel | Collection[BaseModel]")


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
            dto_field = model_field.field_info.extra.get(DTO_FIELD_META_KEY, DTOField())

            def determine_default(_parsed_type: ParsedType, _model_field: ModelField) -> Any:
                if (
                    _model_field.default is Ellipsis
                    or _model_field.default_factory is not None
                    or (_model_field.default is None and not _parsed_type.is_optional)
                ):
                    return Empty

                return _model_field.default

            field_def = FieldDefinition(
                name=key,
                default=determine_default(parsed_type, model_field),
                parsed_type=parsed_type,
                default_factory=model_field.default_factory or Empty,
                dto_field=dto_field,
                unique_model_name=get_fully_qualified_class_name(model_type),
                dto_for=None,
            )

            yield field_def

    @classmethod
    def detect_nested_field(cls, parsed_type: ParsedType) -> bool:
        return parsed_type.is_subclass_of(BaseModel)
