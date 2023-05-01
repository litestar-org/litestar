from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, NewType, TypeVar, cast

from msgspec import Struct, from_builtins

from litestar.dto.factory._backends.abc import AbstractDTOBackend
from litestar.dto.factory._backends.utils import _build_data_from_transfer_data, _build_transfer_instance_from_model
from litestar.serialization import decode_media_type

from .utils import _create_struct_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.dto.factory._backends.types import FieldDefinitionsType
    from litestar.dto.interface import ConnectionContext
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("MsgspecDTOBackend",)


MsgspecField = NewType("MsgspecField", type)
T = TypeVar("T")


class MsgspecDTOBackend(AbstractDTOBackend[Struct]):
    __slots__ = ()

    def create_data_container_type(self, unique_name: str, field_definitions: FieldDefinitionsType) -> type[Struct]:
        return _create_struct_for_field_definitions(unique_name, field_definitions)

    def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> Struct | Collection[Struct]:
        return decode_media_type(  # type:ignore[no-any-return]
            raw, connection_context.request_encoding_type, type_=self.annotation
        )

    def populate_data_from_builtins(self, data: Any) -> Any:
        parsed_data = cast("Struct | Collection[Struct]", from_builtins(data, self.annotation))
        return _build_data_from_transfer_data(self.context.model_type, parsed_data, self.parsed_field_definitions)

    def populate_data_from_raw(self, raw: bytes, connection_context: ConnectionContext) -> T | Collection[T]:
        parsed_data = self.parse_raw(raw, connection_context)
        return _build_data_from_transfer_data(self.context.model_type, parsed_data, self.parsed_field_definitions)

    def encode_data(self, data: Any, connection_context: ConnectionContext) -> LitestarEncodableType:
        if isinstance(data, CollectionsCollection):
            return self.context.parsed_type.origin(  # type:ignore[no-any-return]
                _build_transfer_instance_from_model(datum, self.data_container_type, self.parsed_field_definitions)
                for datum in data  # pyright:ignore
            )
        return _build_transfer_instance_from_model(  # type:ignore[no-any-return]
            data,
            self.data_container_type,
            self.parsed_field_definitions,
        )
