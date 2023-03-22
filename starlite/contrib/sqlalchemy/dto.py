from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped
from typing_extensions import get_args, get_origin

from starlite.dto import AbstractDTO
from starlite.dto.backends.pydantic import PydanticDTOBackend
from starlite.dto.config import DTO_FIELD_META_KEY
from starlite.dto.types import FieldDefinition
from starlite.dto.utils import get_model_type_hints

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator, Iterable

    from sqlalchemy import Column
    from sqlalchemy.orm import RelationshipProperty

    from starlite.enums import MediaType

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
        if mapper is None:  # pragma: no cover
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
                field_name=key, field_type=type_hint, dto_field=elem.info.get(DTO_FIELD_META_KEY)
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

    def to_encodable_type(self, media_type: str | MediaType) -> Any:
        if isinstance(self.data, DeclarativeBase):
            return self.dto_backend.model(**convert_declarative_to_dict(self.data))
        type_ = get_origin(self.annotation) or self.annotation
        return type_(
            self.dto_backend.model(**convert_declarative_to_dict(datum))
            for datum in self.data  # type:ignore[union-attr]
        )


def convert_declarative_to_dict(model: DeclarativeBase) -> dict[str, Any]:
    return {col.name: getattr(model, col.name) for col in model.__table__.columns}
