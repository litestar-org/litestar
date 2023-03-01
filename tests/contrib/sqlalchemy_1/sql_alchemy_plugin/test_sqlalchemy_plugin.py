from typing import Any

import pytest
from sqlalchemy import Column, Integer
from sqlalchemy.orm import Mapper, as_declarative, declarative_base

from starlite.contrib.sqlalchemy_1.plugin import SQLAlchemyPlugin
from starlite.exceptions import ImproperlyConfiguredException

DeclBase = declarative_base()


@as_declarative()
class AsDeclBase:
    ...


class FromAsDeclarative(AsDeclBase):
    __tablename__ = "whatever"
    id = Column(Integer, primary_key=True)


class FromDeclBase(DeclBase):
    __tablename__ = "whatever"
    id = Column(Integer, primary_key=True)


class Plain:
    ...


@pytest.mark.parametrize(
    "item,result",
    [
        (FromAsDeclarative, True),
        (FromAsDeclarative(), True),
        (FromDeclBase, True),
        (FromDeclBase(), True),
        (Plain, False),
        (Plain(), False),
        (None, False),
        ("str", False),
    ],
)
def test_is_plugin_supported_type(item: Any, result: bool) -> None:
    assert SQLAlchemyPlugin.is_plugin_supported_type(item) is result


@pytest.mark.parametrize(
    "item,should_raise",
    [
        (FromAsDeclarative, False),
        (FromAsDeclarative(), True),
        (FromDeclBase, False),
        (FromDeclBase(), True),
        (Plain, True),
        (Plain(), True),
        (None, True),
        ("str", True),
    ],
)
def test_parse_model(item: Any, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            SQLAlchemyPlugin.parse_model(item)
    else:
        assert isinstance(SQLAlchemyPlugin.parse_model(item), Mapper)
