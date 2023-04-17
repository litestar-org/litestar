from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, NewType, TypeVar
from uuid import uuid4

from msgspec import Struct

from litestar.dto.factory.backends.abc import AbstractDTOBackend
from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.serialization import decode_json, decode_msgpack

from .utils import _build_data_from_struct, _build_struct_from_model, _create_msgspec_struct_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.connection import Request
    from litestar.dto.factory.types import FieldDefinitionsType
    from litestar.types.serialization import LitestarEncodableType

__all__ = ["MsgspecDTOBackend"]


MsgspecField = NewType("MsgspecField", type)
StructT = TypeVar("StructT", bound=Struct)
T = TypeVar("T")


class MsgspecDTOBackend(AbstractDTOBackend[Struct]):
    __slots__ = ()

    def parse_raw(self, raw: bytes, media_type: MediaType | str) -> Struct | Collection[Struct]:
        if media_type == MediaType.JSON:
            transfer_data = decode_json(raw, type_=self.annotation)
        elif media_type == MediaType.MESSAGEPACK:
            transfer_data = decode_msgpack(raw, type_=self.annotation)
        else:
            raise SerializationException(f"Unsupported media type: '{media_type}'")
        return transfer_data  # type:ignore[return-value]

    def populate_data_from_raw(self, model_type: type[T], raw: bytes, media_type: MediaType | str) -> T | Collection[T]:
        parsed_data = self.parse_raw(raw, media_type)
        return _build_data_from_struct(model_type, parsed_data, self.field_definitions)

    def encode_data(self, data: Any, connection: Request) -> LitestarEncodableType:
        if isinstance(data, CollectionsCollection):
            return self.parsed_type.origin(  # type:ignore[no-any-return]
                _build_struct_from_model(datum, self.data_container_type) for datum in data  # pyright:ignore
            )
        return _build_struct_from_model(data, self.data_container_type)

    @classmethod
    def from_field_definitions(cls, annotation: Any, field_definitions: FieldDefinitionsType) -> Any:
        return cls(
            annotation, _create_msgspec_struct_for_field_definitions(str(uuid4()), field_definitions), field_definitions
        )
