from __future__ import annotations

from dataclasses import MISSING, fields
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.field import DTO_FIELD_META_KEY
from litestar.dto.factory.types import FieldDefinition
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import ClassVar, Collection, Generator

    from litestar.types.protocols import DataclassProtocol
    from litestar.utils.signature import ParsedType


__all__ = ("DataclassDTO", "DataT")

DataT = TypeVar("DataT", bound="DataclassProtocol | Collection[DataclassProtocol]")
AnyDataclass = TypeVar("AnyDataclass", bound="DataclassProtocol")


class DataclassDTO(AbstractDTOFactory[DataT], Generic[DataT]):
    """Support for domain modelling with dataclasses."""

    __slots__ = ()

    model_type: ClassVar[type[DataclassProtocol]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[DataclassProtocol]) -> Generator[FieldDefinition, None, None]:
        dc_fields = {f.name: f for f in fields(model_type)}
        for key, parsed_type in get_model_type_hints(model_type).items():
            if not (dc_field := dc_fields.get(key)):
                continue

            default = dc_field.default if dc_field.default is not MISSING else Empty

            default_factory = dc_field.default_factory if dc_field.default_factory is not MISSING else None

            field_def = FieldDefinition(
                name=key,
                parsed_type=parsed_type,
                default=default,
                default_factory=default_factory,
                dto_field=dc_field.metadata.get(DTO_FIELD_META_KEY),
                unique_model_name=get_fully_qualified_class_name(model_type),
            )

            yield field_def

    @classmethod
    def detect_nested_field(cls, parsed_type: ParsedType) -> bool:
        return hasattr(parsed_type.annotation, "__dataclass_fields__")
