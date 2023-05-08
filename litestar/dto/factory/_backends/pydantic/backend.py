from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, parse_obj_as

from litestar.dto.factory._backends.abc import AbstractDTOBackend
from litestar.serialization import decode_media_type

from .utils import _create_model_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.dto.factory._backends.types import FieldDefinitionsType
    from litestar.dto.interface import ConnectionContext

__all__ = ("PydanticDTOBackend",)


T = TypeVar("T")


class PydanticDTOBackend(AbstractDTOBackend[BaseModel]):
    __slots__ = ()

    def create_transfer_model_type(self, unique_name: str, field_definitions: FieldDefinitionsType) -> type[BaseModel]:
        return _create_model_for_field_definitions(unique_name, field_definitions)

    def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> BaseModel | Collection[BaseModel]:
        return decode_media_type(  # type:ignore[no-any-return]
            raw, connection_context.request_encoding_type, type_=self.annotation
        )

    def parse_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
        return parse_obj_as(self.annotation, builtins)
