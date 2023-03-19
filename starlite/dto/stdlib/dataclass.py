from __future__ import annotations

from dataclasses import MISSING, fields
from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import Self, get_args

from starlite.dto import AbstractDTO
from starlite.dto.backends.msgspec import MsgspecDTOBackend
from starlite.dto.config import DTO_FIELD_META_KEY
from starlite.dto.types import FieldDefinition
from starlite.dto.utils import get_model_type_hints
from starlite.enums import MediaType
from starlite.serialization import decode_json, encode_json

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator, Iterable

    from starlite.types import DataclassProtocol


__all__ = ("DataclassDTO", "DataT")

DataT = TypeVar("DataT", bound="DataclassProtocol | Iterable[DataclassProtocol]")
AnyDataclass = TypeVar("AnyDataclass", bound="DataclassProtocol")


class DataclassDTO(AbstractDTO[DataT], Generic[DataT]):
    """Support for domain modelling with dataclasses."""

    dto_backend_type = MsgspecDTOBackend
    dto_backend: ClassVar[MsgspecDTOBackend]

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
    def detect_nested(cls, field_definition: FieldDefinition) -> bool:
        args = get_args(field_definition.field_type)
        if not args:
            return hasattr(field_definition.field_type, "__dataclass_fields__")
        return any(hasattr(a, "__dataclass_fields__") for a in args)

    @classmethod
    def from_bytes(cls, raw: bytes, media_type: MediaType | str = MediaType.JSON) -> Self:
        parsed = cls.dto_backend.parse_raw(raw, media_type)
        return cls(data=cls.build_data(cls.annotation, parsed, cls.field_definitions))

    def to_encodable_type(self, media_type: str | MediaType) -> Any:
        return decode_json(encode_json(self.data), self.dto_backend.annotation)
