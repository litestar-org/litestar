from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from typing_extensions import Self

from starlite.dto.interface import DTOInterface
from starlite.types.protocols import DataclassProtocol
from starlite.types.serialization import StarliteEncodableType

if TYPE_CHECKING:
    from typing import Any

    from starlite.connection import Request


@dataclass
class Model:
    a: int
    b: str


class MockDTO(DTOInterface[DataclassProtocol]):
    def to_data_type(self) -> DataclassProtocol:
        return Model(a=1, b="2")

    def to_encodable_type(self, request: Request[Any, Any, Any]) -> bytes | StarliteEncodableType:
        return Model(a=1, b="2")

    @classmethod
    async def from_connection(cls, connection: Request[Any, Any, Any]) -> Self:
        return cls()

    @classmethod
    def from_data(cls, data: DataclassProtocol) -> Self:
        return cls()


class MockReturnDTO(DTOInterface[DataclassProtocol]):
    def to_data_type(self) -> DataclassProtocol:
        raise RuntimeError("Return DTO should have this method called")

    def to_encodable_type(self, request: Request[Any, Any, Any]) -> bytes | StarliteEncodableType:
        return b'{"a": 1, "b": "2"}'

    @classmethod
    async def from_connection(cls, connection: Request[Any, Any, Any]) -> Self:
        raise RuntimeError("Return DTO should have this method called")

    @classmethod
    def from_data(cls, data: DataclassProtocol) -> Self:
        return cls()
