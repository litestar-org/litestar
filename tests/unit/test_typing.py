from __future__ import annotations

from typing import Any, ForwardRef, List, Optional, Tuple, Union

import pytest
from typing_extensions import Annotated

from litestar.typing import ParsedType

from .test_utils.test_signature import T, _check_parsed_type, parsed_type_int, test_type_hints


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
                "inner_types": (parsed_type_int,),
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
                "inner_types": (parsed_type_int,),
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
                "inner_types": (parsed_type_int,),
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
                "inner_types": (parsed_type_int,),
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
                "inner_types": (parsed_type_int,),
            },
        ),
    ],
)
def test_parsed_type_from_annotation(annotation: Any, expected: dict[str, Any]) -> None:
    """Test ParsedType.from_annotation."""
    _check_parsed_type(ParsedType.from_annotation(annotation), expected)


def test_parsed_type_from_union_annotation() -> None:
    """Test ParsedType.from_annotation for Union."""
    annotation = Union[int, List[int]]
    expected = {
        "raw": annotation,
        "annotation": annotation,
        "origin": Union,
        "args": (int, List[int]),
        "metadata": (),
        "safe_generic_origin": Union,
        "inner_types": (ParsedType.from_annotation(int), ParsedType.from_annotation(List[int])),
    }
    _check_parsed_type(ParsedType.from_annotation(annotation), expected)


@pytest.mark.parametrize("value", ["int", ForwardRef("int")])
def test_parsed_type_is_forward_ref_predicate(value: Any) -> None:
    """Test ParsedType with ForwardRef."""
    parsed_type = ParsedType.from_annotation(value)
    assert parsed_type.is_forward_ref is True
    assert parsed_type.annotation == value
    assert parsed_type.origin is None
    assert parsed_type.args == ()
    assert parsed_type.metadata == ()
    assert parsed_type.is_annotated is False
    assert parsed_type.is_required is True
    assert parsed_type.safe_generic_origin is None
    assert parsed_type.inner_types == ()


def test_parsed_type_is_type_var_predicate() -> None:
    """Test ParsedType.is_type_var."""
    assert ParsedType.from_annotation(int).is_type_var is False
    assert ParsedType.from_annotation(T).is_type_var is True
    assert ParsedType.from_annotation(Union[int, T]).is_type_var is False


def test_parsed_type_is_union_predicate() -> None:
    """Test ParsedType.is_union."""
    assert ParsedType.from_annotation(int).is_union is False
    assert ParsedType.from_annotation(Optional[int]).is_union is True
    assert ParsedType.from_annotation(Union[int, None]).is_union is True
    assert ParsedType.from_annotation(Union[int, str]).is_union is True


def test_parsed_type_is_optional_predicate() -> None:
    """Test ParsedType.is_optional."""
    assert ParsedType.from_annotation(int).is_optional is False
    assert ParsedType.from_annotation(Optional[int]).is_optional is True
    assert ParsedType.from_annotation(Union[int, None]).is_optional is True
    assert ParsedType.from_annotation(Union[int, None, str]).is_optional is True
    assert ParsedType.from_annotation(Union[int, str]).is_optional is False


def test_parsed_type_is_subclass_of() -> None:
    """Test ParsedType.is_type_of."""
    assert ParsedType.from_annotation(bool).is_subclass_of(int) is True
    assert ParsedType.from_annotation(bool).is_subclass_of(str) is False
    assert ParsedType.from_annotation(Union[int, str]).is_subclass_of(int) is False
    assert ParsedType.from_annotation(List[int]).is_subclass_of(list) is True
    assert ParsedType.from_annotation(List[int]).is_subclass_of(int) is False
    assert ParsedType.from_annotation(Optional[int]).is_subclass_of(int) is False
    assert ParsedType.from_annotation(Union[bool, int]).is_subclass_of(int) is True


def test_parsed_type_has_inner_subclass_of() -> None:
    """Test ParsedType.has_type_of."""
    assert ParsedType.from_annotation(List[int]).has_inner_subclass_of(int) is True
    assert ParsedType.from_annotation(List[int]).has_inner_subclass_of(str) is False
    assert ParsedType.from_annotation(List[Union[int, str]]).has_inner_subclass_of(int) is False


def test_parsed_type_equality() -> None:
    assert ParsedType.from_annotation(int) == ParsedType.from_annotation(int)
    assert ParsedType.from_annotation(int) == ParsedType.from_annotation(Annotated[int, "meta"])
    assert ParsedType.from_annotation(int) != int
    assert ParsedType.from_annotation(List[int]) == ParsedType.from_annotation(List[int])
    assert ParsedType.from_annotation(List[int]) != ParsedType.from_annotation(List[str])
    assert ParsedType.from_annotation(List[str]) != ParsedType.from_annotation(Tuple[str])
    assert ParsedType.from_annotation(Optional[str]) == ParsedType.from_annotation(Union[str, None])
