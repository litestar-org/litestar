from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, NewType, TypeVar
from uuid import uuid4

from msgspec import Struct

from litestar.dto.factory.backends.abc import AbstractDTOBackend
from litestar.serialization import decode_media_type

from .utils import _build_data_from_struct, _build_struct_from_model, _create_struct_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.connection import Request
    from litestar.dto.factory.types import FieldDefinitionsType
    from litestar.enums import MediaType
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("MsgspecDTOBackend",)


MsgspecField = NewType("MsgspecField", type)
T = TypeVar("T")


class MsgspecDTOBackend(AbstractDTOBackend[Struct]):
    __slots__ = ()

    def parse_raw(self, raw: bytes, media_type: MediaType | str) -> Struct | Collection[Struct]:
        return decode_media_type(raw, media_type, type_=self.annotation)  # type:ignore[no-any-return]

    def populate_data_from_builtins(self, model_type: type[T], data: Any) -> T | Collection[T]:
        raise NotImplementedError("Msgspec backend does not support marshalling types")

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
        return cls(annotation, _create_struct_for_field_definitions(str(uuid4()), field_definitions), field_definitions)
