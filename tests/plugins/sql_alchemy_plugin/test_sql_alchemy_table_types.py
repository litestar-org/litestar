import pytest
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
    TupleType,
    Unicode,
    UnicodeText,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import registry

from starlite import ImproperlyConfiguredException
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin

Base = declarative_base()
mapper_registry = registry()


class DeclarativeModel(Base):
    __tablename__ = "declarative"

    id = Column(Integer, primary_key=True)
    ARRAY_column = Column(ARRAY(String, dimensions=2))
    BIGINT_column = Column(BIGINT)
    BINARY_column = Column(BINARY)
    BLOB_column = Column(BLOB)
    BOOLEAN_column = Column(BOOLEAN)
    BigInteger_column = Column(BigInteger)
    Boolean_column = Column(Boolean)
    CHAR_column = Column(CHAR(length=3))
    CLOB_column = Column(CLOB)
    DATE_column = Column(DATE)
    DATETIME_column = Column(DATETIME)
    DECIMAL_column = Column(DECIMAL)
    Date_column = Column(Date)
    DateTime_column = Column(DateTime)
    Enum_column = Column(Enum)
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
    TupleType_column = Column(TupleType(str, int, bool))
    Unicode_column = Column(Unicode)
    UnicodeText_column = Column(UnicodeText)
    VARBINARY_column = Column(VARBINARY)
    VARCHAR_column = Column(VARCHAR)


imperative_model = Table(
    "imperative",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True),
    Column("ARRAY_column", ARRAY(String, dimensions=2)),
    Column("BIGINT_column", BIGINT),
    Column("BINARY_column", BINARY),
    Column("BLOB_column", BLOB),
    Column("BOOLEAN_column", BOOLEAN),
    Column("BigInteger_column", BigInteger),
    Column("Boolean_column", Boolean),
    Column("CHAR_column", CHAR(length=3)),
    Column("CLOB_column", CLOB),
    Column("DATE_column", DATE),
    Column("DATETIME_column", DATETIME),
    Column("DECIMAL_column", DECIMAL),
    Column("Date_column", Date),
    Column("DateTime_column", DateTime),
    Column("Enum_column", Enum),
    Column("FLOAT_column", FLOAT(asdecimal=True)),
    Column("Float_column", Float),
    Column("INT_column", INT),
    Column("INTEGER_column", INTEGER),
    Column("Integer_column", Integer),
    Column("Interval_column", Interval),
    Column("JSON_column", JSON),
    Column("LargeBinary_column", LargeBinary),
    Column("NCHAR_column", NCHAR),
    Column("NUMERIC_column", NUMERIC),
    Column("NVARCHAR_column", NVARCHAR),
    Column("Numeric_column", Numeric),
    Column("REAL_column", REAL),
    Column("SMALLINT_column", SMALLINT),
    Column("SmallInteger_column", SmallInteger),
    Column("String_column", String),
    Column("TEXT_column", TEXT),
    Column("TIME_column", TIME),
    Column("TIMESTAMP_column", TIMESTAMP),
    Column("Text_column", Text),
    Column("Time_column", Time),
    Column("TupleType_column", TupleType(str, int, bool)),
    Column("Unicode_column", Unicode),
    Column("UnicodeText_column", UnicodeText),
    Column("VARBINARY_column", VARBINARY),
    Column("VARCHAR_column", VARCHAR),
)


def test_sql_alchemy_plugin_model_class_parsing():
    plugin = SQLAlchemyPlugin()
    result = plugin.to_pydantic_model_class(model_class=DeclarativeModel)
    assert issubclass(result, BaseModel)


def test_sql_alchemy_plugin_validatio():
    plugin = SQLAlchemyPlugin()
    with pytest.raises(ImproperlyConfiguredException):
        plugin.to_pydantic_model_class(model_class=imperative_model)

    with pytest.raises(ImproperlyConfiguredException):
        plugin.to_pydantic_model_class(model_class=declarative_base)
