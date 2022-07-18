from typing import Optional

from pydantic import BaseModel

from starlite.types import Partial
from tests import Person

try:
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:
    from typing import _GenericAlias as GenericAlias  # type: ignore


def test_partial() -> None:
    partial = Partial[Person]
    assert partial
    for field in partial.__fields__.values():  # type: ignore
        assert field.allow_none
        assert not field.required
    for field in partial.__annotations__.values():
        assert isinstance(field, GenericAlias)
        assert type(None) in field.__args__


def test_partial_superclass() -> None:
    class Parent(BaseModel):
        foo: int

    class Child(Parent):
        bar: int

    partial_child = Partial[Child]

    for field in partial_child.__fields__.values():  # type: ignore
        assert field.allow_none
        assert not field.required
    assert partial_child.__annotations__ == {
        "foo": Optional[int],
        "bar": Optional[int],
    }
