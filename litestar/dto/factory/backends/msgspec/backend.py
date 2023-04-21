from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, NewType, TypeVar, cast
from uuid import uuid4

from msgspec import Struct, from_builtins

from litestar.dto.factory.backends.abc import AbstractDTOBackend, BackendContext
from litestar.serialization import decode_media_type

from .utils import _build_data_from_struct, _build_struct_from_model, _create_struct_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.connection import Request
    from litestar.enums import MediaType
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("MsgspecDTOBackend",)


MsgspecField = NewType("MsgspecField", type)
T = TypeVar("T")


class MsgspecDTOBackend(AbstractDTOBackend[Struct]):
    __slots__ = ()

    def create_data_container_type(self, context: BackendContext) -> type[Struct]:
        return _create_struct_for_field_definitions(str(uuid4()), context.field_definitions)

    def parse_raw(self, raw: bytes, media_type: MediaType | str) -> Struct | Collection[Struct]:
        return decode_media_type(raw, media_type, type_=self.annotation)  # type:ignore[no-any-return]

    def populate_data_from_builtins(self, data: Any) -> Any:
        parsed_data = cast("Struct | Collection[Struct]", from_builtins(data, self.annotation))
        return _build_data_from_struct(self.context.model_type, parsed_data, self.context.field_definitions)

    def populate_data_from_raw(self, raw: bytes, media_type: MediaType | str) -> T | Collection[T]:
        parsed_data = self.parse_raw(raw, media_type)
        return _build_data_from_struct(self.context.model_type, parsed_data, self.context.field_definitions)

    def encode_data(self, data: Any, connection: Request) -> LitestarEncodableType:
        if isinstance(data, CollectionsCollection):
            return self.context.parsed_type.origin(  # type:ignore[no-any-return]
                _build_struct_from_model(datum, self.data_container_type) for datum in data  # pyright:ignore
            )
        return _build_struct_from_model(data, self.data_container_type)
