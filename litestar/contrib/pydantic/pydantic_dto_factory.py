from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Collection, Generic, TypeVar

from typing_extensions import override

from litestar.dto.base_dto import AbstractDTO
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.dto.field import DTO_FIELD_META_KEY, DTOField
from litestar.exceptions import MissingDependencyException, ValidationException
from litestar.types.empty import Empty

if TYPE_CHECKING:
    from typing import Any, Generator

    from litestar.typing import FieldDefinition


try:
    import pydantic
    from pydantic import ValidationError

    if pydantic.VERSION.startswith("2"):
        from pydantic_core import PydanticUndefined
    else:  # pragma: no cover
        from pydantic.fields import Undefined as PydanticUndefined  # type: ignore
except ImportError as e:
    raise MissingDependencyException("pydantic") from e

__all__ = ("PydanticDTO",)

T = TypeVar("T", bound="pydantic.BaseModel | Collection[pydantic.BaseModel]")


class PydanticDTO(AbstractDTO[T], Generic[T]):
    """Support for domain modelling with Pydantic."""

    @override
    def decode_builtins(self, value: dict[str, Any]) -> Any:
        try:
            return super().decode_builtins(value)
        except ValidationError as ex:
            raise ValidationException(extra=ex.errors()) from ex

    @override
    def decode_bytes(self, value: bytes) -> Any:
        try:
            return super().decode_bytes(value)
        except ValidationError as ex:
            raise ValidationException(extra=ex.errors()) from ex

    @classmethod
    def generate_field_definitions(
        cls, model_type: type[pydantic.BaseModel]
    ) -> Generator[DTOFieldDefinition, None, None]:
        model_field_definitions = cls.get_model_type_hints(model_type)

        if pydantic.VERSION.startswith("1"):  # pragma: no cover
            model_fields: dict[str, pydantic.fields.FieldInfo] = {k: model_field.field_info for k, model_field in model_type.__fields__.items()}  # type: ignore
        else:
            model_fields = dict(model_type.model_fields)

        for field_name, field_info in model_fields.items():
            field_definition = model_field_definitions[field_name]
            dto_field = (field_definition.extra or {}).pop(DTO_FIELD_META_KEY, DTOField())

            if field_info.default is not PydanticUndefined:
                default = field_info.default
            elif field_definition.is_optional:
                default = None
            else:
                default = Empty

            yield replace(
                DTOFieldDefinition.from_field_definition(
                    field_definition=field_definition,
                    dto_field=dto_field,
                    model_name=model_type.__name__,
                    default_factory=field_info.default_factory
                    if field_info.default_factory and field_info.default_factory is not PydanticUndefined  # type: ignore[comparison-overlap]
                    else Empty,
                ),
                default=default,
                name=field_name,
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return field_definition.is_subclass_of(pydantic.BaseModel)
