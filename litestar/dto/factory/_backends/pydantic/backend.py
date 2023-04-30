from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, TypeVar, cast
from uuid import uuid4

from pydantic import BaseModel, parse_obj_as

from litestar.dto.factory._backends.abc import AbstractDTOBackend, BackendContext
from litestar.serialization import decode_media_type

from .utils import _build_data_from_pydantic_model, _create_model_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.dto.interface import ConnectionContext
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("PydanticDTOBackend",)


T = TypeVar("T")


class PydanticDTOBackend(AbstractDTOBackend[BaseModel]):
    __slots__ = ()

    def create_data_container_type(self, context: BackendContext) -> type[BaseModel]:
        return _create_model_for_field_definitions(str(uuid4()), self.parsed_field_definitions)

    def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> BaseModel | Collection[BaseModel]:
        return decode_media_type(  # type:ignore[no-any-return]
            raw, connection_context.request_encoding_type, type_=self.annotation
        )

    def populate_data_from_builtins(self, data: Any) -> T | Collection[T]:
        parsed_data = cast("BaseModel | Collection[BaseModel]", parse_obj_as(self.annotation, data))
        return _build_data_from_pydantic_model(self.context.model_type, parsed_data, self.parsed_field_definitions)

    def populate_data_from_raw(self, raw: bytes, connection_context: ConnectionContext) -> T | Collection[T]:
        parsed_data = self.parse_raw(raw, connection_context)
        return _build_data_from_pydantic_model(self.context.model_type, parsed_data, self.parsed_field_definitions)

    def encode_data(self, data: Any, connection_context: ConnectionContext) -> LitestarEncodableType:
        if isinstance(data, CollectionsCollection):
            return self.context.parsed_type.origin(  # type:ignore[no-any-return]
                self.data_container_type.from_orm(datum) for datum in data  # pyright:ignore
            )
        return self.data_container_type.from_orm(data)
