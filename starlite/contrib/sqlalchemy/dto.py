from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped
from typing_extensions import get_args, get_origin

from starlite.dto.factory.abc import MsgspecBackedDTOFactory
from starlite.dto.factory.config import DTO_FIELD_META_KEY
from starlite.dto.factory.types import FieldDefinition
from starlite.dto.factory.utils import get_model_type_hints

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator, Iterable

    from sqlalchemy import Column
    from sqlalchemy.orm import RelationshipProperty


__all__ = ("SQLAlchemyDTO", "DataT")

DataT = TypeVar("DataT", bound="DeclarativeBase | Iterable[DeclarativeBase]")
AnyDeclarativeT = TypeVar("AnyDeclarativeT", bound="DeclarativeBase")


class SQLAlchemyDTO(MsgspecBackedDTOFactory[DataT], Generic[DataT]):
    """Support for domain modelling with SQLAlchemy."""

    __slots__ = ()

    model_type: ClassVar[type[DeclarativeBase]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[DeclarativeBase]) -> Generator[FieldDefinition, None, None]:
        if (mapper := inspect(model_type)) is None:  # pragma: no cover
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

            if (default := getattr(elem, "default", None)) is None:
                if getattr(elem, "nullable", False):
                    field_def.default = None
            elif default.is_scalar:
                field_def.default = default.arg
            elif default.is_callable:
                field_def.default_factory = lambda d=default: d.arg({})  # type:ignore[misc]
            else:
                raise ValueError("Unexpected default type")

            yield field_def

    @classmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        if args := get_args(field_definition.field_type):
            return any(issubclass(a, DeclarativeBase) for a in args)
        return issubclass(field_definition.field_type, DeclarativeBase)
