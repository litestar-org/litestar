from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import DeclarativeBase

from litestar.contrib.sqlalchemy.dto import SQLAlchemyDTO
from litestar.plugins import SerializationPluginProtocol

from . import _slots_base

if TYPE_CHECKING:
    from litestar.utils.signature import ParsedType


class SQLAlchemySerializationPlugin(SerializationPluginProtocol, _slots_base.SlotsBase):
    __slots__ = ()

    def __init__(self) -> None:
        self._type_dto_map: dict[type[DeclarativeBase], type[SQLAlchemyDTO]] = {}

    @staticmethod
    def supports_type(parsed_type: ParsedType) -> bool:
        return (
            parsed_type.is_collection and parsed_type.has_inner_subclass_of(DeclarativeBase)
        ) or parsed_type.is_subclass_of(DeclarativeBase)

    def create_dto_for_type(self, parsed_type: ParsedType) -> type[SQLAlchemyDTO]:
        # assumes that the type is a container of SQLAlchemy models or a single SQLAlchemy model
        for inner_type in parsed_type.inner_types:
            if inner_type.is_subclass_of(DeclarativeBase):
                annotation = inner_type.annotation
                break
        else:
            annotation = parsed_type.annotation

        if annotation in self._type_dto_map:
            return self._type_dto_map[annotation]

        self._type_dto_map[annotation] = dto_type = SQLAlchemyDTO[annotation]  # type:ignore[valid-type]

        return dto_type
