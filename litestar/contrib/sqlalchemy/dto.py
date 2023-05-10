from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from sqlalchemy import inspect, orm, sql
from sqlalchemy.orm import DeclarativeBase, Mapped

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.field import DTO_FIELD_META_KEY
from litestar.dto.factory.types import FieldDefinition
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import Any, ClassVar, Collection, Generator

    from sqlalchemy import Column
    from sqlalchemy.orm import RelationshipProperty
    from typing_extensions import TypeAlias

    from litestar.utils.signature import ParsedType


__all__ = ("SQLAlchemyDTO", "DataT")

DataT = TypeVar("DataT", bound="DeclarativeBase | Collection[DeclarativeBase]")
AnyDeclarativeT = TypeVar("AnyDeclarativeT", bound="DeclarativeBase")
ElementType: TypeAlias = "Column[Any] | RelationshipProperty[Any]"


class SQLAlchemyDTO(AbstractDTOFactory[DataT], Generic[DataT]):
    """Support for domain modelling with SQLAlchemy."""

    __slots__ = ()

    model_type: ClassVar[type[DeclarativeBase]]

    @classmethod
    def generate_field_definitions(cls, model_type: type[DeclarativeBase]) -> Generator[FieldDefinition, None, None]:
        if (mapper := inspect(model_type)) is None:  # pragma: no cover
            raise RuntimeError("Unexpected `None` value for mapper.")

        columns = mapper.columns
        relationships = mapper.relationships

        # includes SQLAlchemy names and other mapped class names in the forward reference resolution namespace
        namespace = dict(vars(orm))
        namespace.update(vars(sql))
        namespace.update({m.class_.__name__: m.class_ for m in mapper.registry.mappers if m is not mapper})

        for key, parsed_type in get_model_type_hints(model_type, namespace=namespace).items():
            elem: ElementType | None
            elem = columns.get(key, relationships.get(key))  # pyright:ignore
            if elem is None:
                continue

            if parsed_type.origin is Mapped:
                (parsed_type,) = parsed_type.inner_types  # noqa: PLW2901

            default, default_factory = _detect_defaults(elem)

            field_def = FieldDefinition(
                name=key,
                default=default,
                parsed_type=parsed_type,
                default_factory=default_factory,
                dto_field=elem.info.get(DTO_FIELD_META_KEY),
                unique_model_name=get_fully_qualified_class_name(model_type),
            )

            yield field_def

    @classmethod
    def detect_nested_field(cls, parsed_type: ParsedType) -> bool:
        return parsed_type.is_subclass_of(DeclarativeBase)


def _detect_defaults(elem: ElementType) -> tuple[Any, Any]:
    default: Any = Empty
    default_factory: Any = None  # pyright:ignore
    if sqla_default := getattr(elem, "default", None):
        if sqla_default.is_scalar:
            default = sqla_default.arg
        elif sqla_default.is_callable:

            def default_factory(d: Any = sqla_default) -> Any:
                return d.arg({})

        else:
            raise ValueError("Unexpected default type")
    else:
        if getattr(elem, "nullable", False):
            default = None
    return default, default_factory
