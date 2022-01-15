from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from inspect import isclass
from ipaddress import IPv4Network, IPv6Network
from typing import Any, Callable, Dict, List, Tuple, Union
from uuid import UUID

from pydantic import BaseModel, Json, conint, constr, create_model
from typing_extensions import Type

from starlite.exceptions import (
    ImproperlyConfiguredException,
    MissingDependencyException,
)
from starlite.plugins.base import PluginProtocol

try:
    from sqlalchemy import Table, inspect
    from sqlalchemy import types as sqlalchemy_type
    from sqlalchemy.dialects import (
        firebird,
        mssql,
        mysql,
        oracle,
        postgresql,
        sqlite,
        sybase,
    )
    from sqlalchemy.orm import DeclarativeMeta, Mapper, RelationshipProperty
    from sqlalchemy.sql.type_api import TypeEngine
except ImportError as exc:  # pragma: no cover
    raise MissingDependencyException("sqlalchemy is not installed") from exc


class SQLAlchemyPlugin(PluginProtocol[Union[DeclarativeMeta, Table]]):
    def __init__(self) -> None:
        self.model_map: Dict[Any, Type[BaseModel]] = {}

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        """
        This plugin supports only SQLAlchemy declarative models
        """
        return isinstance(value, DeclarativeMeta) or isinstance(value.__class__, DeclarativeMeta)

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
            # firebird
            firebird.CHAR: self.handle_string_type,
            firebird.VARCHAR: self.handle_string_type,
            # mssql
            mssql.BIT: lambda x: bool,
            mssql.DATETIME2: lambda x: datetime,
            mssql.DATETIMEOFFSET: lambda x: datetime,
            mssql.IMAGE: self.handle_string_type,
            mssql.MONEY: lambda x: Decimal,
            mssql.NTEXT: self.handle_string_type,
            mssql.REAL: self.handle_numeric_type,
            mssql.SMALLDATETIME: lambda x: datetime,
            mssql.SMALLMONEY: lambda x: Decimal,
            mssql.SQL_VARIANT: lambda x: str,
            mssql.TIME: lambda x: time,
            mssql.TINYINT: lambda x: int,
            mssql.UNIQUEIDENTIFIER: lambda x: str,
            mssql.VARBINARY: self.handle_string_type,
            mssql.XML: self.handle_string_type,
            # mysql
            mysql.BIGINT: lambda x: int,
            mysql.BIT: lambda x: bool,
            mysql.CHAR: self.handle_string_type,
            mysql.DATETIME: lambda x: datetime,
            mysql.DECIMAL: self.handle_numeric_type,
            mysql.DOUBLE: self.handle_numeric_type,
            mysql.ENUM: lambda x: Enum,
            mysql.FLOAT: self.handle_numeric_type,
            mysql.INTEGER: lambda x: int,
            mysql.JSON: lambda x: Json,
            mysql.LONGBLOB: self.handle_string_type,
            mysql.LONGTEXT: self.handle_string_type,
            mysql.MEDIUMBLOB: self.handle_string_type,
            mysql.MEDIUMINT: lambda x: int,
            mysql.MEDIUMTEXT: self.handle_string_type,
            mysql.NCHAR: self.handle_string_type,
            mysql.NUMERIC: self.handle_numeric_type,
            mysql.NVARCHAR: self.handle_string_type,
            mysql.REAL: self.handle_numeric_type,
            mysql.SET: lambda x: set,
            mysql.SMALLINT: lambda x: int,
            mysql.TEXT: self.handle_string_type,
            mysql.TIME: lambda x: time,
            mysql.TIMESTAMP: lambda x: datetime,
            mysql.TINYBLOB: self.handle_string_type,
            mysql.TINYINT: lambda x: int,
            mysql.TINYTEXT: self.handle_string_type,
            mysql.VARCHAR: self.handle_string_type,
            mysql.YEAR: lambda x: conint(ge=1901, le=2155),
            # oracle
            oracle.BFILE: self.handle_string_type,
            oracle.BINARY_DOUBLE: self.handle_numeric_type,
            oracle.BINARY_FLOAT: self.handle_numeric_type,
            oracle.DATE: lambda x: datetime,  # supports time
            oracle.DOUBLE_PRECISION: self.handle_numeric_type,
            oracle.INTERVAL: lambda x: timedelta,
            oracle.LONG: self.handle_string_type,
            oracle.NCLOB: self.handle_string_type,
            oracle.NUMBER: self.handle_numeric_type,
            oracle.RAW: self.handle_string_type,
            oracle.VARCHAR2: self.handle_string_type,
            oracle.VARCHAR: self.handle_string_type,
            # postgresql
            postgresql.ARRAY: self.handle_list_type,
            postgresql.BIT: lambda x: bool,
            postgresql.BYTEA: self.handle_string_type,
            postgresql.CIDR: lambda x: Union[IPv4Network, IPv6Network],
            postgresql.DATERANGE: lambda x: Tuple[date, date],
            postgresql.DOUBLE_PRECISION: self.handle_numeric_type,
            postgresql.ENUM: lambda x: Enum,
            postgresql.HSTORE: lambda x: Dict[str, str],
            postgresql.INET: lambda x: Union[IPv4Network, IPv6Network],
            postgresql.INT4RANGE: lambda x: Tuple[int, int],
            postgresql.INT8RANGE: lambda x: Tuple[int, int],
            postgresql.INTERVAL: lambda x: timedelta,
            postgresql.JSON: lambda x: Json,
            postgresql.JSONB: lambda x: Json,
            postgresql.MACADDR: lambda x: constr(regex=r"^([A-F0-9]{2}:){5}[A-F0-9]{2}$"),
            postgresql.MONEY: lambda x: Decimal,
            postgresql.NUMRANGE: lambda x: Tuple[Union[int, float], Union[int, float]],
            postgresql.TIME: lambda x: time,
            postgresql.TIMESTAMP: lambda x: datetime,
            postgresql.TSRANGE: lambda x: Tuple[datetime, datetime],
            postgresql.TSTZRANGE: lambda x: Tuple[datetime, datetime],
            postgresql.UUID: lambda x: UUID,
            # sqlite
            sqlite.DATE: lambda x: date,
            sqlite.DATETIME: lambda x: datetime,
            sqlite.JSON: lambda x: Json,
            sqlite.TIME: lambda x: time,
            # sybase
            sybase.BIT: lambda x: bool,
            sybase.IMAGE: self.handle_string_type,
            sybase.MONEY: lambda x: Decimal,
            sybase.SMALLMONEY: lambda x: Decimal,
            sybase.TINYINT: lambda x: int,
            sybase.UNICHAR: self.handle_string_type,
            sybase.UNITEXT: self.handle_string_type,
            sybase.UNIVARCHAR: self.handle_string_type,
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

    def from_pydantic_model_instance(self, model_class: DeclarativeMeta, pydantic_model_instance: BaseModel) -> Any:
        """
        Create an instance of a given model_class using the values stored in the given pydantic_model_instance
        """
        return model_class(**pydantic_model_instance.dict())

    def to_dict(self, model_instance: Any) -> Dict[str, Any]:
        model_class = model_instance.__class__
        pydantic_model = self.model_map.get(model_class) or self.to_pydantic_model_class(model_class=model_class)
        kwargs: Dict[str, Any] = {}
        for field in pydantic_model.__fields__:
            kwargs[field] = getattr(model_instance, field)
        return pydantic_model(**kwargs).dict()
