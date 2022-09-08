import dataclasses
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

    assert len(partial.__fields__) == len(Person.__fields__)  # type: ignore

    for field in partial.__fields__.values():  # type: ignore
        assert field.allow_none
        assert not field.required

    for annotation in partial.__annotations__.values():
        assert isinstance(annotation, GenericAlias)
        assert type(None) in annotation.__args__


@pytest.mark.parametrize("cls", [VanillaDataClassPerson, PydanticDataClassPerson])
def test_partial_dataclass(cls: Any) -> None:
    partial = Partial[cls]  # type: ignore

    assert len(partial.__dataclass_fields__) == len(cls.__dataclass_fields__)  # type: ignore

    for field in partial.__dataclass_fields__.values():  # type: ignore
        assert field.default is None
        assert type(None) in field.type.__args__

    for annotation in partial.__annotations__.values():
        assert isinstance(annotation, GenericAlias)
        assert type(None) in annotation.__args__


def test_partial_pydantic_model_with_superclass() -> None:
    """Test that Partial returns the correct annotations for nested models."""

    class Parent(BaseModel):
        parent_attribute: int

    class Child(Parent):
        child_attribute: int

    partial_child = Partial[Child]

    for field in partial_child.__fields__.values():  # type: ignore
        assert field.allow_none
        assert not field.required

    assert partial_child.__annotations__ == {
        "parent_attribute": Optional[int],
        "child_attribute": Optional[int],
    }


def test_partial_dataclass_with_superclass() -> None:
    """Test that Partial returns the correct annotations for nested models."""

    @dataclasses.dataclass
    class Parent:
        parent_attribute: int

    @dataclasses.dataclass
    class Child(Parent):
        child_attribute: int

    partial_child = Partial[Child]

    for field in partial_child.__dataclass_fields__.values():  # type: ignore
        assert field.default is None
        assert type(None) in field.type.__args__

    assert partial_child.__annotations__ == {
        "parent_attribute": Optional[int],
        "child_attribute": Optional[int],
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
