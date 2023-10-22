from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, ForwardRef, Generic, List, Optional, Tuple, Union

import pytest
from typing_extensions import Annotated, TypedDict

from litestar.typing import FieldDefinition

from .test_utils.test_signature import T, _check_field_definition, field_definition_int, test_type_hints


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (
            int,
            {
                "raw": int,
                "annotation": int,
                "origin": None,
                "args": (),
                "metadata": (),
                "safe_generic_origin": None,
                "inner_types": (),
            },
        ),
        (
            List[int],
            {
                "raw": List[int],
                "annotation": List[int],
                "origin": list,
                "args": (int,),
                "metadata": (),
                "safe_generic_origin": List,
                "inner_types": (field_definition_int,),
            },
        ),
        (
            Annotated[int, "foo"],
            {
                "raw": Annotated[int, "foo"],
                "annotation": int,
                "origin": None,
                "args": (),
                "metadata": ("foo",),
                "safe_generic_origin": None,
                "inner_types": (),
            },
        ),
        (
            Annotated[List[int], "foo"],
            {
                "raw": Annotated[List[int], "foo"],
                "annotation": List[int],
                "origin": list,
                "args": (int,),
                "metadata": ("foo",),
                "safe_generic_origin": List,
                "inner_types": (field_definition_int,),
            },
        ),
        (
            test_type_hints["req_int"],
            {
                "raw": test_type_hints["req_int"],
                "annotation": int,
                "origin": None,
                "args": (),
                "metadata": (),
                "safe_generic_origin": None,
                "inner_types": (),
            },
        ),
        (
            test_type_hints["req_list_int"],
            {
                "raw": test_type_hints["req_list_int"],
                "annotation": List[int],
                "origin": list,
                "args": (int,),
                "metadata": (),
                "safe_generic_origin": List,
                "inner_types": (field_definition_int,),
            },
        ),
        (
            test_type_hints["not_req_int"],
            {
                "raw": test_type_hints["not_req_int"],
                "annotation": int,
                "origin": None,
                "args": (),
                "metadata": (),
                "safe_generic_origin": None,
                "inner_types": (),
            },
        ),
        (
            test_type_hints["not_req_list_int"],
            {
                "raw": test_type_hints["not_req_list_int"],
                "annotation": List[int],
                "origin": list,
                "args": (int,),
                "metadata": (),
                "safe_generic_origin": List,
                "inner_types": (field_definition_int,),
            },
        ),
        (
            test_type_hints["ann_req_int"],
            {
                "raw": test_type_hints["ann_req_int"],
                "annotation": int,
                "origin": None,
                "args": (),
                "metadata": ("foo",),
                "safe_generic_origin": None,
                "inner_types": (),
            },
        ),
        (
            test_type_hints["ann_req_list_int"],
            {
                "raw": test_type_hints["ann_req_list_int"],
                "annotation": List[int],
                "origin": list,
                "args": (int,),
                "metadata": ("foo",),
                "safe_generic_origin": List,
                "inner_types": (field_definition_int,),
            },
        ),
    ],
)
def test_field_definition_from_annotation(annotation: Any, expected: dict[str, Any]) -> None:
    """Test FieldDefinition.from_annotation."""
    _check_field_definition(FieldDefinition.from_annotation(annotation), expected)


def test_field_definition_from_union_annotation() -> None:
    """Test FieldDefinition.from_annotation for Union."""
    annotation = Union[int, List[int]]
    expected = {
        "raw": annotation,
        "annotation": annotation,
        "origin": Union,
        "args": (int, List[int]),
        "metadata": (),
        "safe_generic_origin": Union,
        "inner_types": (FieldDefinition.from_annotation(int), FieldDefinition.from_annotation(List[int])),
    }
    _check_field_definition(FieldDefinition.from_annotation(annotation), expected)


@pytest.mark.parametrize("value", ["int", ForwardRef("int")])
def test_field_definition_is_forward_ref_predicate(value: Any) -> None:
    """Test FieldDefinition with ForwardRef."""
    field_definition = FieldDefinition.from_annotation(value)
    assert field_definition.is_forward_ref is True
    assert field_definition.annotation == value
    assert field_definition.origin is None
    assert field_definition.args == ()
    assert field_definition.metadata == ()
    assert field_definition.is_annotated is False
    assert field_definition.is_required is True
    assert field_definition.safe_generic_origin is None
    assert field_definition.inner_types == ()


def test_field_definition_is_type_var_predicate() -> None:
    """Test FieldDefinition.is_type_var."""
    assert FieldDefinition.from_annotation(int).is_type_var is False
    assert FieldDefinition.from_annotation(T).is_type_var is True
    assert FieldDefinition.from_annotation(Union[int, T]).is_type_var is False  # pyright: ignore


def test_field_definition_is_union_predicate() -> None:
    """Test FieldDefinition.is_union."""
    assert FieldDefinition.from_annotation(int).is_union is False
    assert FieldDefinition.from_annotation(Optional[int]).is_union is True
    assert FieldDefinition.from_annotation(Union[int, None]).is_union is True
    assert FieldDefinition.from_annotation(Union[int, str]).is_union is True


def test_field_definition_is_optional_predicate() -> None:
    """Test FieldDefinition.is_optional."""
    assert FieldDefinition.from_annotation(int).is_optional is False
    assert FieldDefinition.from_annotation(Optional[int]).is_optional is True
    assert FieldDefinition.from_annotation(Union[int, None]).is_optional is True
    assert FieldDefinition.from_annotation(Union[int, None, str]).is_optional is True
    assert FieldDefinition.from_annotation(Union[int, str]).is_optional is False


def test_field_definition_is_dataclass_predicate() -> None:
    """Test FieldDefinition.is_dataclass."""

    class NormalClass:
        ...

    @dataclass
    class NormalDataclass:
        ...

    @dataclass
    class GenericDataclass(Generic[T]):
        ...

    assert FieldDefinition.from_annotation(NormalDataclass).is_dataclass_type is True
    assert FieldDefinition.from_annotation(GenericDataclass).is_dataclass_type is True
    assert FieldDefinition.from_annotation(GenericDataclass[int]).is_dataclass_type is True
    assert FieldDefinition.from_annotation(GenericDataclass[T]).is_dataclass_type is True  # type: ignore[valid-type]
    assert FieldDefinition.from_annotation(NormalClass).is_dataclass_type is False


def test_field_definition_is_typeddict_predicate() -> None:
    """Test FieldDefinition.is_typeddict."""

    class NormalClass:
        ...

    class TypedDictClass(TypedDict):
        ...

    assert FieldDefinition.from_annotation(NormalClass).is_typeddict_type is False
    assert FieldDefinition.from_annotation(TypedDictClass).is_typeddict_type is True

    if sys.version_info >= (3, 11):

        class GenericTypedDictClass(TypedDict, Generic[T]):
            ...

        assert FieldDefinition.from_annotation(GenericTypedDictClass).is_typeddict_type is True
        assert FieldDefinition.from_annotation(GenericTypedDictClass[int]).is_typeddict_type is True
        assert FieldDefinition.from_annotation(GenericTypedDictClass[T]).is_typeddict_type is True


def test_field_definition_is_subclass_of() -> None:
    """Test FieldDefinition.is_type_of."""
    assert FieldDefinition.from_annotation(bool).is_subclass_of(int) is True
    assert FieldDefinition.from_annotation(bool).is_subclass_of(str) is False
    assert FieldDefinition.from_annotation(Union[int, str]).is_subclass_of(int) is False
    assert FieldDefinition.from_annotation(List[int]).is_subclass_of(list) is True
    assert FieldDefinition.from_annotation(List[int]).is_subclass_of(int) is False
    assert FieldDefinition.from_annotation(Optional[int]).is_subclass_of(int) is False
    assert FieldDefinition.from_annotation(Union[bool, int]).is_subclass_of(int) is True


def test_field_definition_has_inner_subclass_of() -> None:
    """Test FieldDefinition.has_type_of."""
    assert FieldDefinition.from_annotation(List[int]).has_inner_subclass_of(int) is True
    assert FieldDefinition.from_annotation(List[int]).has_inner_subclass_of(str) is False
    assert FieldDefinition.from_annotation(List[Union[int, str]]).has_inner_subclass_of(int) is False


def test_field_definition_equality() -> None:
    assert FieldDefinition.from_annotation(int) == FieldDefinition.from_annotation(int)
    assert FieldDefinition.from_annotation(int) == FieldDefinition.from_annotation(Annotated[int, "meta"])
    assert FieldDefinition.from_annotation(int) != int
    assert FieldDefinition.from_annotation(List[int]) == FieldDefinition.from_annotation(List[int])
    assert FieldDefinition.from_annotation(List[int]) != FieldDefinition.from_annotation(List[str])
    assert FieldDefinition.from_annotation(List[str]) != FieldDefinition.from_annotation(Tuple[str])
    assert FieldDefinition.from_annotation(Optional[str]) == FieldDefinition.from_annotation(Union[str, None])


@dataclass
class GenericDataclass(Generic[T]):
    foo: T


@dataclass
class NormalDataclass:
    foo: int


@pytest.mark.parametrize(
    ("annotation", "expected_type_hints"),
    ((GenericDataclass[str], {"foo": str}), (GenericDataclass, {"foo": T}), (NormalDataclass, {"foo": int})),
)
def test_field_definition_get_type_hints(annotation: Any, expected_type_hints: dict[str, Any]) -> None:
    assert (
        FieldDefinition.from_annotation(annotation).get_type_hints(include_extras=True, resolve_generics=True)
        == expected_type_hints
    )
