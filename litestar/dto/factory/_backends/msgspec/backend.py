from __future__ import annotations

import base64
from typing import TYPE_CHECKING, NewType, TypeVar
from uuid import uuid1

from msgspec import Struct, from_builtins

from litestar.dto.factory._backends.abc import AbstractDTOBackend
from litestar.serialization import decode_media_type

from .utils import _create_struct_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.dto.factory._backends.types import FieldDefinitionsType
    from litestar.dto.interface import ConnectionContext

__all__ = ("MsgspecDTOBackend",)


MsgspecField = NewType("MsgspecField", type)
T = TypeVar("T")


def _gen_short_uniqueid(size: int = 6) -> str:
    # Generate a unique ID
    unique_id = str(uuid1()).encode("utf-8")

    # Convert the ID to a short alphanumeric string
    return base64.urlsafe_b64encode(unique_id)[:size].decode("ascii")


class MsgspecDTOBackend(AbstractDTOBackend[Struct]):
    __slots__ = ()

    def create_transfer_model_type(self, unique_name: str, field_definitions: FieldDefinitionsType) -> type[Struct]:
        short_uid: str = _gen_short_uniqueid()
        return _create_struct_for_field_definitions(f"{unique_name}-{short_uid}", field_definitions)

    def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> Struct | Collection[Struct]:
        return decode_media_type(  # type:ignore[no-any-return]
            raw, connection_context.request_encoding_type, type_=self.annotation
        )

    def parse_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
        return from_builtins(builtins, self.annotation)
