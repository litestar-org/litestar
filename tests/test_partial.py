import dataclasses
from typing import Any, ClassVar, Optional, get_type_hints

import pydantic
import pytest
from pydantic import BaseModel
from typing_extensions import TypedDict, get_args

from litestar.exceptions import ImproperlyConfiguredException
from litestar.partial import Partial
from litestar.types.builtin_types import NoneType
from litestar.utils import is_class_var
from tests import (
    AttrsPerson,
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
    class PersonWithClassVar(Person):
        cls_var: ClassVar[int]

    partial = Partial[PersonWithClassVar]

    assert len(partial.__fields__) == len(Person.__fields__)  # type: ignore

    for field in partial.__fields__.values():  # type: ignore
        assert field.allow_none
        assert not field.required

    for annotation in get_type_hints(partial).values():
        if not is_class_var(annotation):
            assert isinstance(annotation, GenericAlias)
            assert NoneType in get_args(annotation)
        else:
            assert NoneType not in get_args(annotation)


def test_partial_vanilla_dataclass() -> None:
    @dataclasses.dataclass
    class VanillaDataClassPersonWithClassVar(VanillaDataClassPerson):
        cls_var: ClassVar[int]

    partial = Partial[VanillaDataClassPersonWithClassVar]

    assert len(dataclasses.fields(VanillaDataClassPersonWithClassVar)) == len(
        dataclasses.fields(VanillaDataClassPerson)
    )

    for annotation in get_type_hints(partial).values():
        if not is_class_var(annotation):
            assert isinstance(annotation, GenericAlias)
            assert NoneType in get_args(annotation)
        else:
            assert NoneType not in get_args(annotation)


def test_partial_pydantic_dataclass() -> None:
    @pydantic.dataclasses.dataclass
    class VanillaDataClassPersonWithClassVar(VanillaDataClassPerson):
        cls_var: ClassVar[int]

    partial = Partial[VanillaDataClassPersonWithClassVar]

    assert len(dataclasses.fields(VanillaDataClassPersonWithClassVar)) == len(
        dataclasses.fields(PydanticDataClassPerson)
    )

    for annotation in get_type_hints(partial).values():
        if not is_class_var(annotation):
            assert isinstance(annotation, GenericAlias)
            assert NoneType in get_args(annotation)
        else:
            assert NoneType not in get_args(annotation)


def test_partial_typeddict() -> None:
    partial = Partial[TypedDictPerson]

    assert len(get_type_hints(partial)) == len(get_type_hints(TypedDictPerson))

    for annotation in get_type_hints(partial).values():
        assert isinstance(annotation, GenericAlias)
        assert NoneType in get_args(annotation)


def test_partial_attrs() -> None:
    class PersonWithClassVar(AttrsPerson):
        cls_var: ClassVar[int]

    partial = Partial[PersonWithClassVar]

    assert len(get_type_hints(partial)) == len(get_type_hints(PersonWithClassVar))

    for annotation in get_type_hints(partial).values():
        if not is_class_var(annotation):
            assert isinstance(annotation, GenericAlias)
            assert NoneType in get_args(annotation)
        else:
            assert NoneType not in get_args(annotation)


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
