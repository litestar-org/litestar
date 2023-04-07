# ruff: noqa: UP006,UP007
from __future__ import annotations

import inspect
from inspect import Parameter
from typing import Any, List, Optional, Union

import pytest
from typing_extensions import Annotated, NotRequired, Required, TypedDict, get_type_hints

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types.builtin_types import NoneType
from litestar.types.empty import Empty
from litestar.types.parsed_signature import ParsedParameter, ParsedSignature, ParsedType
from litestar.utils.signature_parsing import get_fn_type_hints


class _TD(TypedDict):
    req_int: Required[int]
    req_list_int: Required[List[int]]
    not_req_int: NotRequired[int]
    not_req_list_int: NotRequired[List[int]]
    ann_req_int: Required[Annotated[int, "foo"]]
    ann_req_list_int: Required[Annotated[List[int], "foo"]]


test_type_hints = get_type_hints(_TD, include_extras=True)
parsed_type_int = ParsedType.from_annotation(int)


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (int, ParsedType(int, int, None, (), (), False, False, False, None, ())),
        (List[int], ParsedType(List[int], List[int], list, (int,), (), False, False, False, List, (parsed_type_int,))),
        (
            Annotated[int, "foo"],
            ParsedType(Annotated[int, "foo"], int, None, (), ("foo",), True, False, False, None, ()),
        ),
        (
            Annotated[List[int], "foo"],
            ParsedType(
                Annotated[List[int], "foo"],
                List[int],
                list,
                (int,),
                ("foo",),
                True,
                False,
                False,
                List,
                (parsed_type_int,),
            ),
        ),
        (
            test_type_hints["req_int"],
            ParsedType(test_type_hints["req_int"], int, None, (), (), False, True, False, None, ()),
        ),
        (
            test_type_hints["req_list_int"],
            ParsedType(
                test_type_hints["req_list_int"],
                List[int],
                list,
                (int,),
                (),
                False,
                True,
                False,
                List,
                (parsed_type_int,),
            ),
        ),
        (
            test_type_hints["not_req_int"],
            ParsedType(test_type_hints["not_req_int"], int, None, (), (), False, False, True, None, ()),
        ),
        (
            test_type_hints["not_req_list_int"],
            ParsedType(
                test_type_hints["not_req_list_int"],
                List[int],
                list,
                (int,),
                (),
                False,
                False,
                True,
                List,
                (parsed_type_int,),
            ),
        ),
        (
            test_type_hints["ann_req_int"],
            ParsedType(test_type_hints["ann_req_int"], int, None, (), ("foo",), True, True, False, None, ()),
        ),
        (
            test_type_hints["ann_req_list_int"],
            ParsedType(
                test_type_hints["ann_req_list_int"],
                List[int],
                list,
                (int,),
                ("foo",),
                True,
                True,
                False,
                List,
                (parsed_type_int,),
            ),
        ),
    ],
)
def test_parsed_type_from_annotation(annotation: Any, expected: ParsedType) -> None:
    """Test ParsedType.from_annotation."""
    assert ParsedType.from_annotation(annotation) == expected


def test_parsed_type_from_union_annotation() -> None:
    """Test ParsedType.from_annotation for Union."""
    annotation = Union[int, List[int]]
    expected = ParsedType(
        annotation,
        annotation,
        Union,
        (int, List[int]),
        (),
        False,
        False,
        False,
        Union,
        (ParsedType.from_annotation(int), ParsedType.from_annotation(List[int])),
    )
    assert ParsedType.from_annotation(annotation) == expected


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


def test_parsed_type_has_inner_subclass_of() -> None:
    """Test ParsedType.has_type_of."""
    assert ParsedType.from_annotation(List[int]).has_inner_subclass_of(int) is True
    assert ParsedType.from_annotation(List[int]).has_inner_subclass_of(str) is False
    assert ParsedType.from_annotation(List[Union[int, str]]).has_inner_subclass_of(int) is False


def test_parsed_parameter() -> None:
    """Test ParsedParameter."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    parsed_param = ParsedParameter.from_parameter(param, {"foo": int})
    assert parsed_param.name == "foo"
    assert parsed_param.default is Empty
    assert parsed_param.parsed_type.annotation is int


def test_parsed_parameter_raises_improperly_configured_if_no_annotation() -> None:
    """Test ParsedParameter raises ImproperlyConfigured if no annotation."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD)
    with pytest.raises(ImproperlyConfiguredException):
        ParsedParameter.from_parameter(param, {})


def test_parsed_parameter_has_default_predicate() -> None:
    """Test ParsedParameter.has_default."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    parsed_param = ParsedParameter.from_parameter(param, {"foo": int})
    assert parsed_param.has_default is False

    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int, default=42)
    parsed_param = ParsedParameter.from_parameter(param, {"foo": int})
    assert parsed_param.has_default is True


def test_parsed_parameter_annotation_property() -> None:
    """Test ParsedParameter.annotation."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    parsed_param = ParsedParameter.from_parameter(param, {"foo": int})
    assert parsed_param.parsed_type.annotation is int
    assert parsed_param.annotation is int


def test_parsed_signature() -> None:
    """Test ParsedSignature."""

    def fn(foo: int, bar: Optional[List[int]] = None) -> None:
        ...

    parsed_sig = ParsedSignature.from_fn(fn, get_fn_type_hints(fn))
    assert parsed_sig.return_type.annotation is NoneType
    assert parsed_sig.parameters["foo"].parsed_type.annotation is int
    assert parsed_sig.parameters["bar"].parsed_type.args == (List[int], NoneType)
    assert parsed_sig.parameters["bar"].parsed_type.annotation == Union[List[int], NoneType]
    assert parsed_sig.parameters["bar"].default is None
    assert parsed_sig.original_signature == inspect.signature(fn)
