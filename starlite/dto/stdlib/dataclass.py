from __future__ import annotations

from dataclasses import MISSING, fields
from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import get_args

from starlite.dto.abc import MsgspecBackedDTO
from starlite.dto.config import DTO_FIELD_META_KEY
from starlite.dto.types import FieldDefinition
from starlite.dto.utils import get_model_type_hints

if TYPE_CHECKING:
    from typing import ClassVar, Generator, Iterable

    from starlite.types import DataclassProtocol


__all__ = ("DataclassDTO", "DataT")

DataT = TypeVar("DataT", bound="DataclassProtocol | Iterable[DataclassProtocol]")
AnyDataclass = TypeVar("AnyDataclass", bound="DataclassProtocol")


class DataclassDTO(MsgspecBackedDTO[DataT], Generic[DataT]):
    """Support for domain modelling with dataclasses."""

    __slots__ = ()

    model_type: ClassVar[type[DataclassProtocol]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[DataclassProtocol]) -> Generator[FieldDefinition, None, None]:
        dc_fields = {f.name: f for f in fields(model_type)}
        for key, type_hint in get_model_type_hints(model_type).items():
            if not (dc_field := dc_fields.get(key)):
                continue

            field_def = FieldDefinition(
                field_name=key, field_type=type_hint, dto_field=dc_field.metadata.get(DTO_FIELD_META_KEY)
            )

            if dc_field.default is not MISSING:
                field_def.default = dc_field.default

            if dc_field.default_factory is not MISSING:
                field_def.default_factory = dc_field.default_factory

            yield field_def

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        args = get_args(field_definition.field_type)
        if not args:
            return hasattr(field_definition.field_type, "__dataclass_fields__")
        return any(hasattr(a, "__dataclass_fields__") for a in args)
