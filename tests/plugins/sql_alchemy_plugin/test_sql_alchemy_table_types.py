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
)


def test_sql_alchemy_plugin():
    plugin = SQLAlchemyPlugin()
    result = plugin.to_pydantic_model_class(model_class=DeclarativeModel)
    assert issubclass(result, BaseModel)


def test_exception_handling():
    plugin = SQLAlchemyPlugin()
    with pytest.raises(ImproperlyConfiguredException):
        plugin.to_pydantic_model_class(model_class=imperative_model)

    with pytest.raises(ImproperlyConfiguredException):
        plugin.to_pydantic_model_class(model_class=declarative_base)
