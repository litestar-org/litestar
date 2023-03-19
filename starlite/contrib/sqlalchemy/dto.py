from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped
from typing_extensions import Self, get_args, get_origin

from starlite.dto import AbstractDTO, DTOField
from starlite.dto.backends.pydantic import PydanticDTOBackend
from starlite.dto.config import DTO_FIELD_META_KEY
from starlite.dto.types import FieldDefinition
from starlite.dto.utils import get_model_type_hints
from starlite.enums import MediaType
from starlite.exceptions import SerializationException

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator, Iterable

    from pydantic import BaseModel
    from sqlalchemy import Column
    from sqlalchemy.orm import RelationshipProperty


__all__ = ("SQLAlchemyDTO", "DataT")

DataT = TypeVar("DataT", bound="DeclarativeBase | Iterable[DeclarativeBase]")
AnyDeclarativeT = TypeVar("AnyDeclarativeT", bound="DeclarativeBase")


class SQLAlchemyDTO(AbstractDTO[DataT], Generic[DataT]):
    """Support for domain modelling with SQLAlchemy."""

    dto_backend_type = PydanticDTOBackend
    dto_backend: ClassVar[PydanticDTOBackend]

    @classmethod
    def generate_field_definitions(cls, model_type: type[DeclarativeBase]) -> Generator[FieldDefinition, None, None]:
        mapper = inspect(model_type)
        if mapper is None:
            raise RuntimeError("Unexpected `None` value for mapper.")

        columns = mapper.columns
        relationships = mapper.relationships

        for key, type_hint in get_model_type_hints(model_type).items():
            elem: Column[Any] | RelationshipProperty[Any] | None
            elem = columns.get(key, relationships.get(key))  # pyright:ignore
            if elem is None:
                continue

            if get_origin(type_hint) is Mapped:
                (type_hint,) = get_args(type_hint)  # noqa: PLW2901

            field_def = FieldDefinition(
                field_name=key, field_type=type_hint, dto_field=elem.info.get(DTO_FIELD_META_KEY, DTOField())
            )

            default = getattr(elem, "default", None)
            nullable = getattr(elem, "nullable", False)

            if default is None:
                if nullable:
                    field_def.default = None
            elif default.is_scalar:
                field_def.default = default.arg
            elif default.is_callable:
                field_def.default_factory = lambda d=default: d.arg({})  # type:ignore[misc]
            else:
                raise ValueError("Unexpected default type")

            yield field_def

    @classmethod
    def detect_nested(cls, field_definition: FieldDefinition) -> bool:
        args = get_args(field_definition.field_type)
        if not args:
            return issubclass(field_definition.field_type, DeclarativeBase)
        return any(issubclass(a, DeclarativeBase) for a in args)

    @classmethod
    def from_bytes(cls, raw: bytes, media_type: MediaType | str = MediaType.JSON) -> Self:
        if media_type != MediaType.JSON:
            raise SerializationException(f"Unsupported media type: '{media_type}'")
        parsed = cls.dto_backend.parse_raw(raw, media_type)
        return cls(data=cls.build_data(cls.model_type, parsed, cls.field_definitions))

    def to_encodable_type(self, media_type: str | MediaType) -> BaseModel:
        return self.dto_backend.model.from_orm(self.data)  # type:ignore[pydantic-unexpected]
