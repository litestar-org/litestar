from typing import Any

import pytest
import sqlalchemy
from pydantic import BaseModel
from sqlalchemy import (
    ARRAY,
    BIGINT,
    BINARY,
    BLOB,
    BOOLEAN,
    CHAR,
    CLOB,
    DATE,
    DATETIME,
    DECIMAL,
    FLOAT,
    INT,
    INTEGER,
    JSON,
    NCHAR,
    NUMERIC,
    NVARCHAR,
    REAL,
    SMALLINT,
    TEXT,
    TIME,
    TIMESTAMP,
    VARBINARY,
    VARCHAR,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    Interval,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Time,
    Unicode,
    UnicodeText,
)
from sqlalchemy.dialects import mssql, mysql, oracle, postgresql, sqlite
from sqlalchemy.orm import registry
from sqlalchemy.sql.functions import now

# TupleType not a sqlalchemy2-stubs top-level import
from sqlalchemy.sql.sqltypes import TupleType

from starlite.exceptions import ImproperlyConfiguredException
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests import Species
from tests.plugins.sql_alchemy_plugin import SQLAlchemyBase

plugin = SQLAlchemyPlugin()

mapper_registry = registry()


class DeclarativeModel(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    ARRAY_column = Column(ARRAY(String, dimensions=2))
    BIGINT_column = Column(BIGINT)
    BINARY_column = Column(BINARY)
    BLOB_column = Column(BLOB)
    BOOLEAN_column = Column(BOOLEAN, default=True)
    BigInteger_column = Column(BigInteger)
    Boolean_column = Column(Boolean)
    CHAR_column = Column(CHAR(length=3))
    CLOB_column = Column(CLOB)
    DATE_column = Column(DATE)
    DATETIME_column = Column(DATETIME, default=str(now()))
    DECIMAL_column = Column(DECIMAL)
    Date_column = Column(Date)
    DateTime_column = Column(DateTime, default=now)
    Enum_column = Column(Enum(Species))
    FLOAT_column = Column(FLOAT(asdecimal=True))
    Float_column = Column(Float)
    INT_column = Column(INT)
    INTEGER_column = Column(INTEGER)
    Integer_column = Column(Integer)
    Interval_column = Column(Interval)
    JSON_column = Column(JSON)
    LargeBinary_column = Column(LargeBinary)
    NCHAR_column = Column(NCHAR)
    NUMERIC_column = Column(NUMERIC)
    NVARCHAR_column = Column(NVARCHAR)
    Numeric_column = Column(Numeric)
    REAL_column = Column(REAL)
    SMALLINT_column = Column(SMALLINT)
    SmallInteger_column = Column(SmallInteger)
    String_column = Column(String)
    TEXT_column = Column(TEXT)
    TIME_column = Column(TIME)
    TIMESTAMP_column = Column(TIMESTAMP)
    Text_column = Column(Text)
    Time_column = Column(Time)
    # `TupleType[Any]` for 'Value of type variable "_TE" of "TupleType" cannot be "type"  [type-var]'
    TupleType_column = Column(TupleType[Any](str, int, bool))
    Unicode_column = Column(Unicode)
    UnicodeText_column = Column(UnicodeText)
    VARBINARY_column = Column(VARBINARY)
    VARCHAR_column = Column(VARCHAR)
    # mssql
    mssql_BIT_column = Column(mssql.BIT)
    mssql_DATETIME2_column = Column(mssql.DATETIME2)
    mssql_DATETIMEOFFSET_column = Column(mssql.DATETIMEOFFSET)
    mssql_IMAGE_column = Column(mssql.IMAGE)
    mssql_MONEY_column = Column(mssql.MONEY)
    mssql_NTEXT_column = Column(mssql.NTEXT)
    mssql_REAL_column = Column(mssql.REAL)
    mssql_SMALLDATETIME_column = Column(mssql.SMALLDATETIME)
    mssql_SMALLMONEY_column = Column(mssql.SMALLMONEY)
    mssql_SQL_VARIANT_column = Column(mssql.SQL_VARIANT)
    mssql_TIME_column = Column(mssql.TIME)
    mssql_TINYINT_column = Column(mssql.TINYINT)
    mssql_UNIQUEIDENTIFIER_column = Column(mssql.UNIQUEIDENTIFIER)
    mssql_VARBINARY_column = Column(mssql.VARBINARY)
    mssql_XML_column = Column(mssql.XML)
    # mysql
    mysql_BIGINT_column = Column(mysql.BIGINT)
    mysql_BIT_column = Column(mysql.BIT)
    mysql_CHAR_column = Column(mysql.CHAR)
    mysql_DATETIME_column = Column(mysql.DATETIME)
    mysql_DECIMAL_column = Column(mysql.DECIMAL)
    mysql_DOUBLE_column = Column(mysql.DOUBLE)
    mysql_ENUM_column = Column(mysql.ENUM(Species))
    mysql_FLOAT_column = Column(mysql.FLOAT)
    mysql_INTEGER_column = Column(mysql.INTEGER)
    mysql_JSON_column = Column(mysql.JSON)
    mysql_LONGBLOB_column = Column(mysql.LONGBLOB)
    mysql_LONGTEXT_column = Column(mysql.LONGTEXT)
    mysql_MEDIUMBLOB_column = Column(mysql.MEDIUMBLOB)
    mysql_MEDIUMINT_column = Column(mysql.MEDIUMINT)
    mysql_MEDIUMTEXT_column = Column(mysql.MEDIUMTEXT)
    mysql_NCHAR_column = Column(mysql.NCHAR)
    mysql_NUMERIC_column = Column(mysql.NUMERIC)
    mysql_NVARCHAR_column = Column(mysql.NVARCHAR)
    mysql_REAL_column = Column(mysql.REAL)
    mysql_SET_column = Column(mysql.SET)
    mysql_SMALLINT_column = Column(mysql.SMALLINT)
    mysql_TEXT_column = Column(mysql.TEXT)
    mysql_TIME_column = Column(mysql.TIME)
    mysql_TIMESTAMP_column = Column(mysql.TIMESTAMP)
    mysql_TINYBLOB_column = Column(mysql.TINYBLOB)
    mysql_TINYINT_column = Column(mysql.TINYINT)
    mysql_TINYTEXT_column = Column(mysql.TINYTEXT)
    mysql_VARCHAR_column = Column(mysql.VARCHAR)
    mysql_YEAR_column = Column(mysql.YEAR)
    # oracle
    oracle_BFILE_column = Column(oracle.BFILE)
    oracle_BINARY_DOUBLE_column = Column(oracle.BINARY_DOUBLE)
    oracle_BINARY_FLOAT_column = Column(oracle.BINARY_FLOAT)
    oracle_DATE_column = Column(oracle.DATE)
    oracle_DOUBLE_PRECISION_column = Column(oracle.DOUBLE_PRECISION)
    oracle_INTERVAL_column = Column(oracle.INTERVAL)
    oracle_LONG_column = Column(oracle.LONG)
    oracle_NCLOB_column = Column(oracle.NCLOB)
    oracle_NUMBER_column = Column(oracle.NUMBER)
    oracle_RAW_column = Column(oracle.RAW)
    oracle_VARCHAR2_column = Column(oracle.VARCHAR2)
    oracle_VARCHAR_column = Column(oracle.VARCHAR)
    # postgresql
    postgresql_ARRAY_column = Column(postgresql.ARRAY(String, dimensions=2))
    postgresql_BIT_column: bytes = Column(postgresql.BIT)
    postgresql_BYTEA_column = Column(postgresql.BYTEA)
    postgresql_CIDR_column: str = Column(postgresql.CIDR)
    postgresql_DATERANGE_column = Column(postgresql.DATERANGE)
    postgresql_DOUBLE_PRECISION_column = Column(postgresql.DOUBLE_PRECISION)
    postgresql_ENUM_column = Column(postgresql.ENUM(Species))
    postgresql_HSTORE_column = Column(postgresql.HSTORE)
    postgresql_INET_column: str = Column(postgresql.INET)
    postgresql_INT4RANGE_column = Column(postgresql.INT4RANGE)
    postgresql_INT8RANGE_column = Column(postgresql.INT8RANGE)
    postgresql_INTERVAL_column = Column(postgresql.INTERVAL)
    postgresql_JSON_column = Column(postgresql.JSON)
    postgresql_JSONB_column = Column(postgresql.JSONB)
    postgresql_MACADDR_column: str = Column(postgresql.MACADDR)
    postgresql_MONEY_column: str = Column(postgresql.MONEY)
    postgresql_NUMRANGE_column = Column(postgresql.NUMRANGE)
    postgresql_TIME_column = Column(postgresql.TIME)
    postgresql_TIMESTAMP_column = Column(postgresql.TIMESTAMP)
    postgresql_TSRANGE_column = Column(postgresql.TSRANGE)
    postgresql_TSTZRANGE_column = Column(postgresql.TSTZRANGE)
    postgresql_UUID_column: postgresql.UUID = Column(postgresql.UUID)
    # sqlite
    sqlite_DATE_column = Column(sqlite.DATE)
    sqlite_DATETIME_column = Column(sqlite.DATETIME)
    sqlite_JSON_column = Column(sqlite.JSON)
    sqlite_TIME_column = Column(sqlite.TIME)


imperative_model = Table(
    "imperative",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True),
)


def test_sql_alchemy_plugin_model_class_parsing() -> None:
    result = plugin.to_data_container_class(model_class=DeclarativeModel)
    assert issubclass(result, BaseModel)


def test_sql_alchemy_plugin_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        plugin.to_data_container_class(model_class=imperative_model)

    class MyClass(BaseModel):
        id: int

    with pytest.raises(ImproperlyConfiguredException):
        plugin.to_data_container_class(model_class=MyClass)


def test_provider_validation() -> None:
    class MyStrColumn(sqlalchemy.String):
        pass

    class ModelWithCustomColumn(SQLAlchemyBase):
        id = Column(Integer, primary_key=True)
        custom_column = Column(MyStrColumn)

    with pytest.raises(ImproperlyConfiguredException):
        plugin.to_data_container_class(model_class=ModelWithCustomColumn)
