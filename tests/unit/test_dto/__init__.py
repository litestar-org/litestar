from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Collection, Generator, cast

from litestar._openapi.schema_generation import SchemaCreator
from litestar.dto import AbstractDTO, DTOFieldDefinition
from litestar.openapi.spec import Reference, Schema
from litestar.types.protocols import DataclassProtocol
from litestar.types.serialization import LitestarEncodableType
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from typing import Any


@dataclass
class Model:
    a: int
    b: str


class MockDTO(AbstractDTO[DataclassProtocol]):
    def decode(self, value: Any) -> Model:
        return Model(a=1, b="2")

    def encode(self, data: DataclassProtocol | Collection[DataclassProtocol]) -> bytes | LitestarEncodableType:
        return Model(a=1, b="2")

    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        return Schema()

    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
        yield cast("DTOFieldDefinition", DTOFieldDefinition.from_annotation(Any))

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return False


class MockReturnDTO(AbstractDTO[DataclassProtocol]):
    def decode(self, value: Any) -> Any:
        raise RuntimeError("Return DTO should not have this method called")

    def encode(self, data: DataclassProtocol | Collection[DataclassProtocol]) -> bytes | LitestarEncodableType:
        return b'{"a": 1, "b": "2"}'

    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        return Schema()

    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
        yield cast("DTOFieldDefinition", DTOFieldDefinition.from_annotation(Any))

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return False
