from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from inspect import getmodule
from typing import TYPE_CHECKING, Generic, TypeVar, cast

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped
from typing_extensions import Self, get_args, get_origin, get_type_hints

from starlite.enums import MediaType
from starlite.exceptions import SerializationException
from starlite.dto import AbstractDTO, DTOField, Purpose
from starlite.dto.backends.pydantic import PydanticDTOBackend
from starlite.dto.types import FieldDefinition, NestedFieldDefinition

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from pydantic import BaseModel
    from sqlalchemy import Column
    from sqlalchemy.orm import Mapper, RelationshipProperty
    from sqlalchemy.sql.base import ReadOnlyColumnCollection
    from sqlalchemy.util import ReadOnlyProperties

    from starlite.dto.types import FieldDefinitionsType


__all__ = ("SQLAlchemyDTO", "ModelT")

DTO_INFO_KEY = "__dto__"

ModelT = TypeVar("ModelT", bound="DeclarativeBase")
AnyDeclarativeT = TypeVar("AnyDeclarativeT", bound="DeclarativeBase")


class SQLAlchemyDTO(AbstractDTO[ModelT], Generic[ModelT]):
    """Support for domain modelling with SQLAlchemy."""

    dto_backend_type = PydanticDTOBackend
    dto_backend: ClassVar[PydanticDTOBackend]

    @classmethod
    def parse_model(
        cls, model_type: type[DeclarativeBase], nested_depth: int = 0, recursive_depth: int = 0
    ) -> FieldDefinitionsType:
        mapper = inspect(cls.model_type)
        if mapper is None:
            raise RuntimeError("Unexpected `None` value for mapper.")
        columns = mapper.columns
        relationships = mapper.relationships
        fields: dict[str, FieldDefinition | NestedFieldDefinition] = {}
        for key, type_hint in get_type_hints(model_type, localns=_get_localns(model_type)).items():
            elem = _get_sqlalchemy_element(key, columns, relationships)
            if elem is None:
                continue

            dto_field = _get_dto_field(elem)

            field_type = type_hint
            if get_origin(field_type) is Mapped:
                (field_type,) = get_args(type_hint)

            if cls.should_exclude_field(key, field_type, dto_field):
                continue

            field_definition = FieldDefinition(field_type=field_type)
            if cls.config.purpose is not Purpose.READ:
                set_field_definition_default(field_definition, elem)

            if cls._detect_nested(field_type):
                nested_field_definition = cls._handle_nested(field_definition, nested_depth, recursive_depth)
                if nested_field_definition is not None:
                    fields[key] = nested_field_definition
                continue

            fields[key] = field_definition
        return fields

    @classmethod
    def _detect_nested(cls, field_type: type) -> bool:
        args = get_args(field_type)
        if not args:
            return issubclass(field_type, DeclarativeBase)
        return any(issubclass(a, DeclarativeBase) for a in args)

    @classmethod
    def _handle_nested(
        cls, field_definition: FieldDefinition, nested_depth: int, recursive_depth: int
    ) -> NestedFieldDefinition | None:
        if nested_depth == cls.config.max_nested_depth:
            return None

        args = get_args(field_definition.field_type)
        origin = get_origin(field_definition.field_type)
        nested = NestedFieldDefinition(
            field_definition=field_definition,
            origin=origin,
            args=args,
            nested_type=args[0] if args else field_definition.field_type,
        )

        is_recursive = nested.is_recursive(cls.model_type)
        if is_recursive and recursive_depth == cls.config.max_nested_recursion:
            return None

        nested.nested_field_definitions = cls.parse_model(
            nested.nested_type, nested_depth + 1, recursive_depth + is_recursive
        )
        return nested

    @classmethod
    def from_bytes(cls, raw: bytes, media_type: MediaType | str = MediaType.JSON) -> Self:
        if media_type != MediaType.JSON:
            raise SerializationException(f"Unsupported media type: '{media_type}'")
        parsed = cls.dto_backend.raw_to_dict(raw, media_type)
        return cls(data=cls._to_mapped(cls.model_type, parsed, cls.field_definitions))

    def to_encodable_type(self, media_type: str | MediaType) -> BaseModel:
        return self.dto_backend.model.from_orm(self.data)  # type:ignore[pydantic-unexpected]

    @classmethod
    def _to_mapped(
        cls, model_type: type[AnyDeclarativeT], data: MutableMapping[str, Any], field_definitions: FieldDefinitionsType
    ) -> AnyDeclarativeT:
        """Create an instance of `model_type`.

        Fill the bound SQLAlchemy model recursively with values from
        the serde instance.
        """
        for k, v in data.items():
            field_definition = field_definitions[k]
            if isinstance(field_definition, FieldDefinition):
                continue

            if isinstance(v, MutableMapping):
                data[k] = cls._to_mapped(field_definition.nested_type, v, field_definition.nested_field_definitions)
            elif isinstance(v, Iterable):
                if field_definition.origin is None:
                    raise RuntimeError("Unexpected origin value for collection type.")
                data[k] = field_definition.origin(
                    cls._to_mapped(field_definition.nested_type, item, field_definition.nested_field_definitions)
                    for item in v
                )

        return model_type(**data)


def set_field_definition_default(field_definition: FieldDefinition, elem: Column | RelationshipProperty) -> None:
    default = getattr(elem, "default", None)
    nullable = getattr(elem, "nullable", False)

    if default is None:
        if nullable:
            field_definition.default = None
        return

    if default.is_scalar:
        field_definition.default = default.arg
    elif default.is_callable:
        field_definition.default_factory = lambda: default.arg({})  # type:ignore[union-attr]
    else:
        raise ValueError("Unexpected default type")


def _get_dto_field(elem: Column | RelationshipProperty) -> DTOField:
    return elem.info.get(DTO_INFO_KEY, DTOField())


def _inspect_model(
    model: type[DeclarativeBase],
) -> tuple[ReadOnlyColumnCollection[str, Column], ReadOnlyProperties[RelationshipProperty]]:
    mapper = cast("Mapper", inspect(model))
    columns = mapper.columns
    relationships = mapper.relationships
    return columns, relationships


def _get_sqlalchemy_element(
    key: str,
    columns: ReadOnlyColumnCollection[str, Column],
    relationships: ReadOnlyProperties[RelationshipProperty],
) -> Column | RelationshipProperty | None:
    column = columns.get(key)
    return column if column is not None else relationships.get(key)


def _get_localns(model: type[DeclarativeBase]) -> dict[str, Any]:
    model_module = getmodule(model)
    return vars(model_module) if model_module is not None else {}
