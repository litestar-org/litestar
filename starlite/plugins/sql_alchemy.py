from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from inspect import isclass
from typing import Any, Callable, Dict, List, Tuple, Union, Optional

from pydantic import BaseModel, constr, create_model
from sqlalchemy.sql.type_api import TypeEngine
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
except ImportError as exc:  # pragma: no cover
    raise MissingDependencyException("sqlalchemy is not installed") from exc


class SQLAlchemyPlugin(PluginProtocol[DeclarativeMeta]):
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

    def handle_list_type(self, column_type: sqlalchemy_type.ARRAY) -> Type:
        """
        Handles the SQLAlchemy Array type
        """
        list_type: Type = self.get_pydantic_type(column_type=column_type.item_type)

        dimensions = column_type.dimensions or 1
        while dimensions > 0:
            list_type = List[list_type]
            dimensions -= 1
        return list_type

    def handle_tuple_type(self, column_type: sqlalchemy_type.TupleType) -> Type:
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

    def handle_relationships(self, mapper: Mapper, field_definitions: Dict[str, Tuple[Any, Any]], regenerate_models: bool = False, is_child: bool = False) -> None:
        model = self.model_map[mapper.entity]
        self_refs: List[Tuple[str, RelationshipProperty]] = []
        regular_refs: List[Tuple[str, RelationshipProperty]] = []
        for name, relationship_property in mapper.relationships.items():
            if relationship_property.entity.entity is mapper.entity:
                self_refs.append((name, relationship_property))
            else:
                regular_refs.append((name, relationship_property))
        for name, relationship_property in self_refs:
            if relationship_property.uselist:
                field_definitions[name] = (List[self.model_map[mapper.entity]], ...)
            else:
                field_definitions[name] = (self.model_map[mapper.entity], ...)
        self.model_map[mapper.entity] = create_model(model.__name__, **field_definitions)
        for name, relationship_property in regular_refs:
            relation_type = self.to_pydantic_model_class(
                model_class=relationship_property.mapper.entity, regenerate_models=not is_child, is_child=True
            )
            if relationship_property.uselist:
                field_definitions[name] = (List[relation_type], ...)
            else:
                field_definitions[name] = (relation_type, ...)
            self.model_map[mapper.entity] = create_model(model.__name__, **field_definitions)
        if regular_refs and not is_child and not regenerate_models:
            self.to_pydantic_model_class(model_class=mapper.entity, field_definitions=field_definitions, regenerate_models=True)

    def to_pydantic_model_class(self, model_class: DeclarativeMeta, **kwargs: Any) -> Type[BaseModel]:
        """
        Generates a pydantic model for a given SQLAlchemy declarative table and any nested relations.
        """
        if not isclass(model_class) or not isinstance(model_class, DeclarativeMeta):
            raise ImproperlyConfiguredException(
                "Unsupported 'model_class' kwarg: "
                "only classes inheriting from SQLAlchemy 'DeclarativeMeta' are supported"
            )
        mapper: Mapper = inspect(model_class)
        regenerate_models = kwargs.pop("regenerate_models", False)
        if regenerate_models or mapper.entity not in self.model_map:
            field_definitions = kwargs.pop("field_definitions", {})
            for name, column in mapper.columns.items():
                if column.default is not None:
                    field_definitions[name] = (self.get_pydantic_type(column.type), column.default)
                elif column.nullable:
                    field_definitions[name] = (self.get_pydantic_type(column.type), None)
                else:
                    field_definitions[name] = (self.get_pydantic_type(column.type), ...)
            # we first generate a pydantic model with relationship values set to Any, so we have a reference we can pass
            if mapper.relationships:
                if mapper.entity not in self.model_map:
                    for name, relationship_property in mapper.relationships.items():
                        field_definitions[name] = (self.model_map.get(relationship_property.mapper.entity, Any), ...)
                    self.model_map[mapper.entity] = create_model(model_class.__name__, **field_definitions)
                self.handle_relationships(mapper=mapper, field_definitions=field_definitions, regenerate_models=regenerate_models, **kwargs)
        return self.model_map[mapper.entity]
