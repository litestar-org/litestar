from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Collection, Generator, get_type_hints

from litestar._openapi.schema_generation import SchemaCreator
from litestar.dto import AbstractDTO, DTOField, DTOFieldDefinition
from litestar.openapi.spec import Reference, Schema
from litestar.types.serialization import LitestarEncodableType
from litestar.typing import FieldDefinition


@dataclass
class Model:
    a: int
    b: str


class TestModelDataDTO(AbstractDTO[Model]):
    def decode(self, value: Any) -> Model:
        return Model(a=1, b="2")

    def encode(self, data: Model | Collection[Model]) -> bytes | LitestarEncodableType:
        return Model(a=1, b="2")

    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        return Schema()

    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
        for k, v in get_type_hints(model_type).items():
            yield DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=v, name=k),
                model_name="Model",
                default_factory=None,
                dto_field=DTOField(),
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return False


class TestModelReturnDTO(AbstractDTO[Model]):
    def decode(self, value: Any) -> Any:
        raise RuntimeError("Return DTO should not have this method called")

    def encode(self, data: Model | Collection[Model]) -> bytes | LitestarEncodableType:
        return b'{"a": 1, "b": "2"}'

    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        return Schema()

    @classmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
        for k, v in get_type_hints(model_type).items():
            yield DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=v, name=k),
                model_name="Model",
                default_factory=None,
                dto_field=DTOField(),
            )

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        return False
