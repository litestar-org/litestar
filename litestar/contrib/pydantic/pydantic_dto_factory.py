from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Collection, Generic, TypeVar

from typing_extensions import TypeAlias, override

from litestar.contrib.pydantic.utils import is_pydantic_undefined
from litestar.contrib.pydantic.pydantic_schema_plugin import PYDANTIC_TYPE_MAP
from litestar.dto.base_dto import AbstractDTO
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.dto.field import DTO_FIELD_META_KEY, DTOField
from litestar.exceptions import MissingDependencyException, ValidationException
from litestar.openapi.spec.enums import OpenAPIType
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from typing import Any, Generator
    from litestar.typing import FieldDefinition

try:
    import pydantic as _  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("pydantic") from e


try:
    import pydantic as pydantic_v2
    from pydantic import ValidationError as ValidationErrorV2
    from pydantic import v1 as pydantic_v1
    from pydantic.v1 import ValidationError as ValidationErrorV1

    ModelType: TypeAlias = "pydantic_v1.BaseModel | pydantic_v2.BaseModel"

except ImportError:
    import pydantic as pydantic_v1  # type: ignore[no-redef]

    pydantic_v2 = Empty  # type: ignore[assignment]
    from pydantic import ValidationError as ValidationErrorV1  # type: ignore[assignment]

    ValidationErrorV2 = ValidationErrorV1  # type: ignore[assignment, misc]
    ModelType = "pydantic_v1.BaseModel"  # type: ignore[misc]


T = TypeVar("T", bound="ModelType | Collection[ModelType]")


__all__ = ("PydanticDTO",)

_DOWNTYPE_MAP: dict[OpenAPIType, type[Any]] = {
    OpenAPIType.STRING: str,
    OpenAPIType.INTEGER: int,
    OpenAPIType.BOOLEAN: bool,
    OpenAPIType.OBJECT: str,
    OpenAPIType.NUMBER: float,
}


class PydanticDTO(AbstractDTO[T], Generic[T]):
    """Support for domain modelling with Pydantic."""

    @override
    def decode_builtins(self, value: dict[str, Any]) -> Any:
        try:
            return super().decode_builtins(value)
        except (ValidationErrorV2, ValidationErrorV1) as ex:
            raise ValidationException(extra=ex.errors()) from ex

    @override
    def decode_bytes(self, value: bytes) -> Any:
        try:
            return super().decode_bytes(value)
        except (ValidationErrorV2, ValidationErrorV1) as ex:
            raise ValidationException(extra=ex.errors()) from ex

    @classmethod
    def generate_field_definitions(
        cls, model_type: type[pydantic_v1.BaseModel | pydantic_v2.BaseModel]
    ) -> Generator[DTOFieldDefinition, None, None]:
        model_field_definitions = cls.get_model_type_hints(model_type)

        model_fields: dict[str, pydantic_v1.fields.FieldInfo | pydantic_v2.fields.FieldInfo]
        try:
            model_fields = dict(model_type.model_fields)  # type: ignore[union-attr]
        except AttributeError:
            model_fields = {
                k: model_field.field_info
                for k, model_field in model_type.__fields__.items()  # type: ignore[union-attr]
            }

        for field_name, field_info in model_fields.items():
            field_definition = model_field_definitions[field_name]

            # downtype pydantic types for validation in msgspec
            #
            # If an annotation is a specialized generic, e.g., `Json[dict[str, Any]]`, then
            # field_definition.annotation will be `dict[str, Any]` and the metadata will be
            # `(Json(),)` - that is, the metadata will be an _instance_ of `Json`, not the
            # type itself. So we check for that case and use the type of the metadata instead
            # of the annotation, if it exists in the `PYDANTIC_TYPE_MAP`.
            annotation = next(
                (type(t) for t in field_definition.metadata if type(t) in PYDANTIC_TYPE_MAP),
                field_definition.annotation,
            )
            if annotation in PYDANTIC_TYPE_MAP:
                open_api_type = PYDANTIC_TYPE_MAP[annotation].type
                if isinstance(open_api_type, OpenAPIType):
                    field_definition = FieldDefinition.from_kwarg(
                        annotation=_DOWNTYPE_MAP[open_api_type], name=field_name
                    )

            dto_field = (field_definition.extra or {}).pop(DTO_FIELD_META_KEY, DTOField())

            if not is_pydantic_undefined(field_info.default):
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
                    if field_info.default_factory and not is_pydantic_undefined(field_info.default_factory)
                    else None,
                ),
                default=default,
                name=field_name,
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        if pydantic_v2 is not Empty:  # type: ignore[comparison-overlap]
            return field_definition.is_subclass_of((pydantic_v1.BaseModel, pydantic_v2.BaseModel))
        return field_definition.is_subclass_of(pydantic_v1.BaseModel)  # type: ignore[unreachable]
