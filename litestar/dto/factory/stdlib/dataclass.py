from __future__ import annotations

from dataclasses import MISSING, fields
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.field import DTO_FIELD_META_KEY
from litestar.dto.factory.types import FieldDefinition
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fqdn

if TYPE_CHECKING:
    from typing import Any, ClassVar, Collection, Generator

    from litestar.types.protocols import DataclassProtocol


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

            default: Any = Empty
            default_factory: Any = Empty

            if dc_field.default is not MISSING:
                default = dc_field.default

            if dc_field.default_factory is not MISSING:
                default_factory = dc_field.default_factory

            field_def = FieldDefinition(
                name=key,
                parsed_type=parsed_type,
                default=default,
                default_factory=default_factory,
                dto_field=dc_field.metadata.get(DTO_FIELD_META_KEY),
                model_fqdn=get_fqdn(model_type),
            )

            yield field_def

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        if not field_definition.parsed_type.inner_types:
            return hasattr(field_definition.annotation, "__dataclass_fields__")
        return any(hasattr(t.annotation, "__dataclass_fields__") for t in field_definition.parsed_type.inner_types)
