from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import DeclarativeBase

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.plugins import SerializationPluginProtocol

from . import _slots_base

if TYPE_CHECKING:
    from litestar.typing import FieldDefinition


class SQLAlchemySerializationPlugin(SerializationPluginProtocol, _slots_base.SlotsBase):
    def __init__(self) -> None:
        self._type_dto_map: dict[type[DeclarativeBase], type[SQLAlchemyDTO[Any]]] = {}

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        return (
            field_definition.is_collection and field_definition.has_inner_subclass_of(DeclarativeBase)
        ) or field_definition.is_subclass_of(DeclarativeBase)

    def create_dto_for_type(self, field_definition: FieldDefinition) -> type[SQLAlchemyDTO[Any]]:
        # assumes that the type is a container of SQLAlchemy models or a single SQLAlchemy model
        annotation = next(
            (
                inner_type.annotation
                for inner_type in field_definition.inner_types
                if inner_type.is_subclass_of(DeclarativeBase)
            ),
            field_definition.annotation,
        )
        if annotation in self._type_dto_map:
            return self._type_dto_map[annotation]

        self._type_dto_map[annotation] = dto_type = SQLAlchemyDTO[annotation]  # type:ignore[valid-type]

        return dto_type
