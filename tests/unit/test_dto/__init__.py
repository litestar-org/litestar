from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar._openapi.schema_generation import SchemaCreator
from litestar.dto.interface import ConnectionContext, DTOInterface, HandlerContext
from litestar.dto.types import ForType
from litestar.openapi.spec import Reference, Schema
from litestar.types.protocols import DataclassProtocol
from litestar.types.serialization import LitestarEncodableType

if TYPE_CHECKING:
    from typing import Any


@dataclass
class Model:
    a: int
    b: str


class MockDTO(DTOInterface):
    def __init__(self, connection_context: ConnectionContext) -> None:
        super().__init__(connection_context=connection_context)

    def builtins_to_data_type(self, builtins: Any) -> Model:
        return Model(a=1, b="2")

    def bytes_to_data_type(self, raw: bytes) -> Model:
        return Model(a=1, b="2")

    def data_to_encodable_type(self, data: DataclassProtocol) -> bytes | LitestarEncodableType:
        return Model(a=1, b="2")

    @classmethod
    def create_openapi_schema(
        cls, dto_for: ForType, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        return Schema()

    @classmethod
    def on_registration(cls, handler_context: HandlerContext) -> None:
        return None


class MockReturnDTO(DTOInterface):
    def __init__(self, connection_context: ConnectionContext) -> None:
        super().__init__(connection_context=connection_context)

    def builtins_to_data_type(self, builtins: Any) -> Model:
        raise RuntimeError("Return DTO should not have this method called")

    def bytes_to_data_type(self, raw: bytes) -> Any:
        raise RuntimeError("Return DTO should not have this method called")

    def data_to_encodable_type(self, data: DataclassProtocol) -> bytes | LitestarEncodableType:
        return b'{"a": 1, "b": "2"}'

    @classmethod
    def create_openapi_schema(
        cls, dto_for: ForType, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        return Schema()

    @classmethod
    def on_registration(cls, handler_context: HandlerContext) -> None:
        return None
