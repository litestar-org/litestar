from typing import Any, Optional

import pytest
from pydantic import BaseModel

from starlite.exceptions import ImproperlyConfiguredException
from starlite.typing import Partial
from tests import Person, PydanticDataClassPerson, VanillaDataClassPerson

try:
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:
    from typing import _GenericAlias as GenericAlias  # type: ignore


def test_partial_pydantic_model() -> None:
    partial = Partial[Person]

    assert partial.__fields__  # type: ignore

    for field in partial.__fields__.values():  # type: ignore
        assert field.allow_none
        assert not field.required

    for field in partial.__annotations__.values():
        assert isinstance(field, GenericAlias)
        assert type(None) in field.__args__


def test_partial_pydantic_model_with_superclass() -> None:
    """Test that Partial returns the correct annotations for nested models."""

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


class Foo:
    bar: int


@pytest.mark.parametrize(
    "cls, should_raise",
    [(Foo, True), (Person, False), (VanillaDataClassPerson, False), (PydanticDataClassPerson, False)],
)
def test_validation(cls: Any, should_raise: bool) -> None:
    """Test that Partial returns no annotations for classes that don't inherit
    from BaseModel."""
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            Partial[cls]()  # type: ignore
    else:
        Partial[cls]()  # type: ignore
