from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from typing_extensions import Self

from litestar.dto.interface import DTOInterface
from litestar.types.protocols import DataclassProtocol
from litestar.types.serialization import LitestarEncodableType

if TYPE_CHECKING:
    from typing import Any, TypeAlias

    from litestar.connection import Request

AnyRequest: TypeAlias = "Request[Any, Any, Any]"


@dataclass
class Model:
    a: int
    b: str


class MockDTO(DTOInterface):
    def to_data_type(self) -> Model:
        return Model(a=1, b="2")

    def to_encodable_type(self) -> bytes | LitestarEncodableType:
        return Model(a=1, b="2")

    @classmethod
    def from_builtins(cls, data: Any, connection: Request[Any, Any, Any]) -> Self:
        return cls()

    @classmethod
    def from_bytes(cls, raw: bytes, connection: AnyRequest) -> Self:
        return cls()

    @classmethod
    def from_data(cls, data: DataclassProtocol, connection: AnyRequest) -> Self:
        return cls()


class MockReturnDTO(DTOInterface):
    def to_data_type(self) -> Any:
        raise RuntimeError("Return DTO should not have this method called")

    def to_encodable_type(self) -> bytes | LitestarEncodableType:
        return b'{"a": 1, "b": "2"}'

    @classmethod
    def from_bytes(cls, raw: bytes, connection: AnyRequest) -> Self:
        raise RuntimeError("Return DTO should not have this method called")

    @classmethod
    def from_data(cls, data: DataclassProtocol, connection: AnyRequest) -> Self:
        return cls()
