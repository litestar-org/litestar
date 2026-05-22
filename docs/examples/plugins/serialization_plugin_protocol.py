from __future__ import annotations

from dataclasses import dataclass
from typing import get_args, get_origin

from litestar import Litestar, get
from litestar.dto import AbstractDTO, DataclassDTO
from litestar.plugins import SerializationPlugin
from litestar.typing import FieldDefinition


@dataclass
class Company:
    id: int
    name: str


class CompanySerializationPlugin(SerializationPlugin):
    def __init__(self) -> None:
        self._type_dto_map: dict[type, type[AbstractDTO]] = {}

    @staticmethod
    def _unwrap_collection(annotation: object) -> object:
        if get_origin(annotation) in (list, tuple, set):
            return next(iter(get_args(annotation)), annotation)
        return annotation

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        annotation = self._unwrap_collection(field_definition.annotation)
        return isinstance(annotation, type) and issubclass(annotation, Company)

    def create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]:
        annotation = self._unwrap_collection(field_definition.annotation)
        assert isinstance(annotation, type)
        if (cached := self._type_dto_map.get(annotation)) is not None:
            return cached
        dto_type: type[AbstractDTO] = DataclassDTO[annotation]
        self._type_dto_map[annotation] = dto_type
        return dto_type


@get("/", sync_to_thread=False)
def get_company() -> Company:
    return Company(id=1, name="ACME")


app = Litestar(route_handlers=[get_company], plugins=[CompanySerializationPlugin()])
