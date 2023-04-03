# ruff: noqa: UP006,UP007
from __future__ import annotations

from inspect import Parameter
from typing import Any, List, Optional, Union

import pytest
from typing_extensions import Annotated, NotRequired, Required, TypedDict, get_type_hints

from starlite.types.builtin_types import NoneType
from starlite.types.empty import Empty
from starlite.types.parsed_signature import ParsedParameter, ParsedSignature, ParsedType
from starlite.utils.signature_parsing import get_fn_type_hints


class _TD(TypedDict):
    req_int: Required[int]
    req_list_int: Required[List[int]]
    not_req_int: NotRequired[int]
    not_req_list_int: NotRequired[List[int]]
    ann_req_int: Required[Annotated[int, "foo"]]
    ann_req_list_int: Required[Annotated[List[int], "foo"]]


test_type_hints = get_type_hints(_TD, include_extras=True)


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (int, ParsedType(int, int, None, (), (), False, False, False, None)),
        (List[int], ParsedType(List[int], List[int], list, (int,), (), False, False, False, List)),
        (Annotated[int, "foo"], ParsedType(Annotated[int, "foo"], int, None, (), ("foo",), True, False, False, None)),
        (
            Annotated[List[int], "foo"],
            ParsedType(Annotated[List[int], "foo"], List[int], list, (int,), ("foo",), True, False, False, List),
        ),
        (
            test_type_hints["req_int"],
            ParsedType(test_type_hints["req_int"], int, None, (), (), False, True, False, None),
        ),
        (
            test_type_hints["req_list_int"],
            ParsedType(test_type_hints["req_list_int"], List[int], list, (int,), (), False, True, False, List),
        ),
        (
            test_type_hints["not_req_int"],
            ParsedType(test_type_hints["not_req_int"], int, None, (), (), False, False, True, None),
        ),
        (
            test_type_hints["not_req_list_int"],
            ParsedType(test_type_hints["not_req_list_int"], List[int], list, (int,), (), False, False, True, List),
        ),
        (
            test_type_hints["ann_req_int"],
            ParsedType(test_type_hints["ann_req_int"], int, None, (), ("foo",), True, True, False, None),
        ),
        (
            test_type_hints["ann_req_list_int"],
            ParsedType(test_type_hints["ann_req_list_int"], List[int], list, (int,), ("foo",), True, True, False, List),
        ),
    ],
)
def test_parsed_type_from_annotation(annotation: Any, expected: ParsedType) -> None:
    """Test ParsedType.from_annotation."""
    assert ParsedType.from_annotation(annotation) == expected


def test_parsed_parameter() -> None:
    """Test ParsedParameter."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    parsed_param = ParsedParameter.from_parameter(param, {"foo": int})
    assert parsed_param.name == "foo"
    assert parsed_param.default is Empty
    assert parsed_param.annotation.annotation is int


def test_parsed_signature() -> None:
    """Test ParsedSignature."""

    def fn(foo: int, bar: Optional[List[int]] = None) -> None:
        ...

    parsed_sig = ParsedSignature.from_fn(fn, get_fn_type_hints(fn))
    assert parsed_sig.return_annotation.annotation is NoneType
    assert parsed_sig.parameters["foo"].annotation.annotation is int
    assert parsed_sig.parameters["bar"].annotation.args == (List[int], NoneType)
    assert parsed_sig.parameters["bar"].annotation.annotation == Union[List[int], NoneType]
    assert parsed_sig.parameters["bar"].default is None
