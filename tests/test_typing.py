import dataclasses
from typing import Any, Optional, get_type_hints

import pytest
from pydantic import BaseModel
from typing_extensions import TypedDict, get_args

from starlite.exceptions import ImproperlyConfiguredException
from starlite.types.builtin_types import NoneType
from starlite.types.partial import Partial
from tests import (
    Person,
    PydanticDataClassPerson,
    TypedDictPerson,
    VanillaDataClassPerson,
)

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

    for annotation in get_type_hints(partial).values():
        assert isinstance(annotation, GenericAlias)
        assert NoneType in get_args(annotation)


@pytest.mark.parametrize("cls", [VanillaDataClassPerson, PydanticDataClassPerson])
def test_partial_dataclass(cls: Any) -> None:
    partial = Partial[cls]

    assert len(partial.__dataclass_fields__) == len(cls.__dataclass_fields__)  # type: ignore

    for field in partial.__dataclass_fields__.values():  # type: ignore
        assert field.default is None
        assert NoneType in get_args(field.type)

    for annotation in get_type_hints(partial).values():
        assert isinstance(annotation, GenericAlias)
        assert NoneType in get_args(annotation)


def test_partial_typeddict() -> None:
    partial = Partial[TypedDictPerson]

    assert len(get_type_hints(partial)) == len(get_type_hints(TypedDictPerson))

    for annotation in get_type_hints(partial).values():
        assert isinstance(annotation, GenericAlias)
        assert NoneType in get_args(annotation)


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

    assert get_type_hints(partial_child) == {
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
        assert NoneType in get_args(field.type)

    assert get_type_hints(partial_child) == {"parent_attribute": Optional[int], "child_attribute": Optional[int]}


def test_partial_typeddict_with_superclass() -> None:
    class Parent(TypedDict, total=True):
        parent_attribute: int

    class Child(Parent):
        child_attribute: int

    partial_child = Partial[Child]

    assert get_type_hints(partial_child) == {"parent_attribute": Optional[int], "child_attribute": Optional[int]}


class Foo:
    bar: int


@pytest.mark.parametrize(
    "cls, should_raise",
    ((Foo, True), (Person, False), (VanillaDataClassPerson, False), (PydanticDataClassPerson, False)),
)
def test_validation(cls: Any, should_raise: bool) -> None:
    """Test that Partial returns no annotations for classes that don't inherit from BaseModel."""
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            Partial[cls]()
    else:
        Partial[cls]()
