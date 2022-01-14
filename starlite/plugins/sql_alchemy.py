from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from inspect import isclass
from typing import Any, Callable, Dict, List, Tuple, Union

from pydantic import BaseModel, constr, create_model
from typing_extensions import Type

from starlite.exceptions import (
    ImproperlyConfiguredException,
    MissingDependencyException,
)
from starlite.plugins.base import PluginProtocol

try:
    from sqlalchemy import Table, inspect
    from sqlalchemy import types as sqlalchemy_type
    from sqlalchemy.orm import DeclarativeMeta, Mapper, RelationshipProperty
    from sqlalchemy.sql.type_api import TypeEngine
except ImportError as exc:  # pragma: no cover
    raise MissingDependencyException("sqlalchemy is not installed") from exc


class SQLAlchemyPlugin(PluginProtocol[Union[DeclarativeMeta, Table]]):
    def __init__(self) -> None:
        self.model_map: Dict[Any, Type[BaseModel]] = {}

    @staticmethod
    def handle_string_type(column_type: Union[sqlalchemy_type.String, sqlalchemy_type._Binary]) -> Type:
        """
        Handles the SQLAlchemy String types, including Blob and Binaric types
        """
        if column_type.length is not None:
            return constr(max_length=column_type.length)
        return str

    @staticmethod
    def handle_numeric_type(column_type: sqlalchemy_type.Numeric) -> Type:
        """
        Handles the SQLAlchemy non-int Numeric types
        """
        if column_type.asdecimal:
            return Decimal
        return float

    def handle_list_type(self, column_type: sqlalchemy_type.ARRAY) -> Any:
        """
        Handles the SQLAlchemy Array type
        """
        list_type: Any = self.get_pydantic_type(column_type=column_type.item_type)

        dimensions = column_type.dimensions or 1
        while dimensions > 0:
            list_type = List[list_type]
            dimensions -= 1
        return list_type

    def handle_tuple_type(self, column_type: sqlalchemy_type.TupleType) -> Any:
        """
        Handles the SQLAlchemy Tuple type
        """
        types = [self.get_pydantic_type(column_type=t) for t in column_type.types]
        return Tuple[tuple(types)]

    @property
    def providers_map(self) -> Dict[Type[TypeEngine], Callable[[Union[TypeEngine, Type[TypeEngine]]], Any]]:
        """
        A map of SQLAlchemy column types to provider functions.

        This method is separated to allow for easy overriding in subclasses.
        """
        return {
            sqlalchemy_type.ARRAY: self.handle_list_type,
            sqlalchemy_type.BIGINT: lambda x: int,
            sqlalchemy_type.BINARY: self.handle_string_type,
            sqlalchemy_type.BLOB: self.handle_string_type,
            sqlalchemy_type.BOOLEAN: lambda x: bool,
            sqlalchemy_type.BigInteger: lambda x: int,
            sqlalchemy_type.Boolean: lambda x: bool,
            sqlalchemy_type.CHAR: self.handle_string_type,
            sqlalchemy_type.CLOB: self.handle_string_type,
            sqlalchemy_type.DATE: lambda x: date,
            sqlalchemy_type.DATETIME: lambda x: datetime,
            sqlalchemy_type.DECIMAL: self.handle_numeric_type,
            sqlalchemy_type.Date: lambda x: date,
            sqlalchemy_type.DateTime: lambda x: datetime,
            sqlalchemy_type.Enum: lambda x: Enum,
            sqlalchemy_type.FLOAT: self.handle_numeric_type,
            sqlalchemy_type.Float: self.handle_numeric_type,
            sqlalchemy_type.INT: lambda x: int,
            sqlalchemy_type.INTEGER: lambda x: int,
            sqlalchemy_type.Integer: lambda x: int,
            sqlalchemy_type.Interval: lambda x: timedelta,
            sqlalchemy_type.JSON: lambda x: dict,
            sqlalchemy_type.LargeBinary: self.handle_string_type,
            sqlalchemy_type.NCHAR: self.handle_string_type,
            sqlalchemy_type.NUMERIC: self.handle_numeric_type,
            sqlalchemy_type.NVARCHAR: self.handle_string_type,
            sqlalchemy_type.Numeric: self.handle_numeric_type,
            sqlalchemy_type.REAL: self.handle_numeric_type,
            sqlalchemy_type.SMALLINT: lambda x: int,
            sqlalchemy_type.SmallInteger: lambda x: int,
            sqlalchemy_type.String: self.handle_string_type,
            sqlalchemy_type.TEXT: self.handle_string_type,
            sqlalchemy_type.TIME: lambda x: time,
            sqlalchemy_type.TIMESTAMP: lambda x: datetime,
            sqlalchemy_type.Text: self.handle_string_type,
            sqlalchemy_type.Time: lambda x: time,
            sqlalchemy_type.TupleType: self.handle_tuple_type,
            sqlalchemy_type.Unicode: self.handle_string_type,
            sqlalchemy_type.UnicodeText: self.handle_string_type,
            sqlalchemy_type.VARBINARY: self.handle_string_type,
            sqlalchemy_type.VARCHAR: self.handle_string_type,
        }

    def get_pydantic_type(self, column_type: Any) -> Any:
        """
        Given a Column.type value, return a type supported by pydantic
        """

        column_type_class = column_type if isclass(column_type) else column_type.__class__
        if issubclass(column_type_class, TypeEngine):
            try:
                provider = self.providers_map[column_type_class]
                return provider(column_type)
            except KeyError as e:
                raise ImproperlyConfiguredException("Unsupported Column type, please extend the provider table.") from e
        return type(column_type)

    def create_relationship(self, relationship_property: RelationshipProperty, regenerate_models: bool) -> Any:
        """Creates a pydantic model for a related entity"""
        relation_type: Any = self.model_map.get(relationship_property.mapper.entity) or self.to_pydantic_model_class(
            model_class=relationship_property.mapper.entity, regenerate_models=regenerate_models, is_child=True
        )
        if relationship_property.uselist:
            return List[relation_type]
        return relation_type

    def handle_relationships(
        self,
        mapper: Mapper,
        field_definitions: Dict[str, Tuple[Any, Any]],
        regenerate_models: bool = False,
        is_child: bool = False,
    ) -> None:
        """
        Handles entity relationships, e.g. One-to-Many, Many-to-Many.

        This requires recursion and repetition, o the code here is unavoidably difficult to parse.
        """
        model = self.model_map[mapper.entity]
        self_refs: List[Tuple[str, RelationshipProperty]] = []
        regular_refs: List[Tuple[str, RelationshipProperty]] = []
        # The loop below separates regular relationship references and self references.
        # Self references are when a model has a relationship to itself. For example, a User has an attribute "friends",
        # which refers to several other Users and vice-versa.
        for name, relationship_property in mapper.relationships.items():
            if relationship_property.entity.entity is mapper.entity:
                self_refs.append((name, relationship_property))
            else:
                regular_refs.append((name, relationship_property))
        for name, relationship_property in self_refs:
            self_model: Any = self.model_map[mapper.entity]
            if relationship_property.uselist:
                field_definitions[name] = (List[self_model], ...)
            else:
                field_definitions[name] = (self_model, ...)
        self.model_map[mapper.entity] = create_model(model.__name__, **field_definitions)  # type: ignore
        for name, relationship_property in regular_refs:
            field_definitions[name] = (
                self.create_relationship(relationship_property=relationship_property, regenerate_models=not is_child),
                ...,
            )
            self.model_map[mapper.entity] = create_model(model.__name__, **field_definitions)  # type: ignore
            if relationship_property.back_populates:
                # we have to update the created relation from the top-level, i.e. from the side of the parent, after it
                # has already been created. Otherwise we will have old refernces to a different version of the parent model
                relation_model = self.model_map[relationship_property.mapper.entity]
                relation_field_definition = {k: (v.outer_type_, ...) for k, v in relation_model.__fields__.items()}
                relation_field_definition[relationship_property.back_populates] = (self.model_map[mapper.entity], ...)
                self.model_map[relationship_property.mapper.entity] = create_model(  # type: ignore
                    relation_model.__name__, **relation_field_definition
                )
                field_definitions[name] = (
                    self.create_relationship(relationship_property=relationship_property, regenerate_models=True),
                    ...,
                )
                self.model_map[mapper.entity] = create_model(model.__name__, **field_definitions)  # type: ignore
        if regular_refs and not is_child and not regenerate_models:
            self.to_pydantic_model_class(
                model_class=mapper.entity, field_definitions=field_definitions, regenerate_models=True
            )

    def parse_model(self, model_class: DeclarativeMeta) -> Mapper:
        """
        Validates that the passed in model_class is an SQLAlchemy declarative model, and returns a Mapper of it
        """
        if not isinstance(model_class, DeclarativeMeta):
            raise ImproperlyConfiguredException(
                "Unsupported 'model_class' kwarg: " "only subclasses of the SQLAlchemy `DeclarativeMeta` are supported"
            )
        return inspect(model_class)

    def to_pydantic_model_class(self, model_class: DeclarativeMeta, **kwargs: Any) -> Type[BaseModel]:
        """
        Generates a pydantic model for a given SQLAlchemy declarative table and any nested relations.
        """
        mapper = self.parse_model(model_class=model_class)
        regenerate_models = kwargs.pop("regenerate_models", False)
        if mapper.entity not in self.model_map or regenerate_models:
            field_definitions = kwargs.pop("field_definitions", {})
            for name, column in mapper.columns.items():
                if column.default is not None:
                    field_definitions[name] = (self.get_pydantic_type(column.type), column.default)
                elif column.nullable:
                    field_definitions[name] = (self.get_pydantic_type(column.type), None)
                else:
                    field_definitions[name] = (self.get_pydantic_type(column.type), ...)
            if mapper.relationships:
                if mapper.entity not in self.model_map:
                    for name, relationship_property in mapper.relationships.items():
                        field_definitions[name] = (self.model_map.get(relationship_property.mapper.entity, Any), ...)
                    # we generate a pydantic model with relationship values set to
                    # either already created entities or Any.
                    # We need to do this here, because we need the reference.
                    self.model_map[mapper.entity] = create_model(model_class.__name__, **field_definitions)
                self.handle_relationships(
                    mapper=mapper, field_definitions=field_definitions, regenerate_models=regenerate_models, **kwargs
                )
            else:
                self.model_map[mapper.entity] = create_model(model_class.__name__, **field_definitions)
        return self.model_map[mapper.entity]
