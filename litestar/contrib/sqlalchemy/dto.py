from __future__ import annotations

from functools import singledispatchmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from sqlalchemy import Column, inspect, orm, sql
from sqlalchemy.ext.associationproxy import AssociationProxy, AssociationProxyExtensionType
from sqlalchemy.orm import (
    ColumnProperty,
    DeclarativeBase,
    InspectionAttr,
    Mapped,
    NotExtension,
    QueryableAttribute,
    RelationshipProperty,
)

from litestar.dto.factory.abc import AbstractDTOFactory
from litestar.dto.factory.field import DTO_FIELD_META_KEY, DTOField, Mark
from litestar.dto.factory.types import FieldDefinition
from litestar.dto.factory.utils import get_model_type_hints
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import Any, ClassVar, Collection, Generator

    from typing_extensions import TypeAlias

    from litestar.typing import ParsedType

__all__ = ("SQLAlchemyDTO",)

T = TypeVar("T", bound="DeclarativeBase | Collection[DeclarativeBase]")
ElementType: TypeAlias = "Column[Any] | RelationshipProperty[Any]"

SQLA_NS = {**vars(orm), **vars(sql)}


class SQLAlchemyDTO(AbstractDTOFactory[T], Generic[T]):
    """Support for domain modelling with SQLAlchemy."""

    __slots__ = ()

    model_type: ClassVar[type[DeclarativeBase]]

    @singledispatchmethod
    @classmethod
    def handle_orm_descriptor(
        cls,
        extension_type: NotExtension | AssociationProxyExtensionType,
        orm_descriptor: InspectionAttr,
        key: str,
        parsed_type: ParsedType,
        model_name: str,
    ) -> FieldDefinition:
        raise NotImplementedError(f"Unsupported extension type: {extension_type}")

    @handle_orm_descriptor.register(NotExtension)
    @classmethod
    def _(
        cls,
        extension_type: NotExtension,
        key: str,
        orm_descriptor: InspectionAttr,
        parsed_type: ParsedType,
        model_name: str,
    ) -> FieldDefinition:
        if not isinstance(orm_descriptor, QueryableAttribute):
            raise NotImplementedError(f"Unexpected descriptor type for '{extension_type}': '{orm_descriptor}'")

        elem: ElementType
        if isinstance(orm_descriptor.property, ColumnProperty):
            if not isinstance(orm_descriptor.property.expression, Column):
                raise NotImplementedError(f"Expected 'Column', got: '{orm_descriptor.property.expression}'")
            elem = orm_descriptor.property.expression
        elif isinstance(orm_descriptor.property, RelationshipProperty):
            elem = orm_descriptor.property
        else:
            raise NotImplementedError(f"Unhandled property type: '{orm_descriptor.property}'")

        default, default_factory = _detect_defaults(elem)

        if parsed_type.origin is Mapped:
            (parsed_type,) = parsed_type.inner_types
        else:
            raise NotImplementedError(f"Expected 'Mapped' origin, got: '{parsed_type.origin}'")

        return FieldDefinition(
            name=key,
            default=default,
            parsed_type=parsed_type,
            default_factory=default_factory,
            dto_field=elem.info.get(DTO_FIELD_META_KEY),
            unique_model_name=model_name,
        )

    @handle_orm_descriptor.register(AssociationProxyExtensionType)
    @classmethod
    def _(
        cls,
        extension_type: AssociationProxyExtensionType,
        key: str,
        orm_descriptor: InspectionAttr,
        parsed_type: ParsedType,
        model_name: str,
    ) -> FieldDefinition:
        if not isinstance(orm_descriptor, AssociationProxy):
            raise NotImplementedError(f"Unexpected descriptor type '{orm_descriptor}' for '{extension_type}'")

        if parsed_type.origin is AssociationProxy:
            (parsed_type,) = parsed_type.inner_types
        else:
            raise NotImplementedError(f"Expected 'AssociationProxy' origin, got: '{parsed_type.origin}'")

        return FieldDefinition(
            name=key,
            default=Empty,
            parsed_type=parsed_type,
            default_factory=None,
            dto_field=orm_descriptor.info.get(DTO_FIELD_META_KEY, DTOField(mark=Mark.READ_ONLY)),
            unique_model_name=model_name,
        )

    @classmethod
    def generate_field_definitions(cls, model_type: type[DeclarativeBase]) -> Generator[FieldDefinition, None, None]:
        if (mapper := inspect(model_type)) is None:  # pragma: no cover
            raise RuntimeError("Unexpected `None` value for mapper.")

        # includes SQLAlchemy names and other mapped class names in the forward reference resolution namespace
        namespace = {**SQLA_NS, **{m.class_.__name__: m.class_ for m in mapper.registry.mappers if m is not mapper}}
        model_type_hints = get_model_type_hints(model_type, namespace=namespace)
        model_name = get_fully_qualified_class_name(model_type)

        for key, orm_descriptor in mapper.all_orm_descriptors.items():
            parsed_type = model_type_hints[key]

            yield cls.handle_orm_descriptor(orm_descriptor.extension_type, key, orm_descriptor, parsed_type, model_name)

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
