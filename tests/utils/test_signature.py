# ruff: noqa: UP006,UP007
from __future__ import annotations

import inspect
from inspect import Parameter
from typing import Any, ForwardRef, List, Optional, Tuple, TypeVar, Union

import pytest
from typing_extensions import Annotated, NotRequired, Required, TypedDict, get_type_hints

from litestar.enums import RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.file_system import BaseLocalFileSystem
from litestar.params import Body
from litestar.static_files import StaticFiles
from litestar.types.asgi_types import Receive, Scope, Send
from litestar.types.builtin_types import NoneType
from litestar.types.empty import Empty
from litestar.utils.signature import (
    ParsedParameter,
    ParsedSignature,
    ParsedType,
    get_fn_type_hints,
    infer_request_encoding_from_parameter,
)

T = TypeVar("T")


def test_get_fn_type_hints_asgi_app() -> None:
    app = StaticFiles(is_html_mode=False, directories=[], file_system=BaseLocalFileSystem())
    assert get_fn_type_hints(app) == {"scope": Scope, "receive": Receive, "send": Send, "return": NoneType}


def func(a: int, b: str, c: float) -> None:
    ...


class C:
    def __init__(self, a: int, b: str, c: float) -> None:
        ...

    def method(self, a: int, b: str, c: float) -> None:
        ...

    def __call__(self, a: int, b: str, c: float) -> None:
        ...


@pytest.mark.parametrize("fn", [func, C, C(1, "2", 3.0).method, C(1, "2", 3.0)])
def test_get_fn_type_hints(fn: Any) -> None:
    assert get_fn_type_hints(fn) == {"a": int, "b": str, "c": float, "return": NoneType}


def test_get_fn_type_hints_class_no_init() -> None:
    """Test that get_fn_type_hints works with classes that don't have an __init__ method.

    Ref: https://github.com/litestar-org/litestar/issues/1504
    """

    class C:
        ...

    assert get_fn_type_hints(C) == {}


class _TD(TypedDict):
    req_int: Required[int]
    req_list_int: Required[List[int]]
    not_req_int: NotRequired[int]
    not_req_list_int: NotRequired[List[int]]
    ann_req_int: Required[Annotated[int, "foo"]]
    ann_req_list_int: Required[Annotated[List[int], "foo"]]


test_type_hints = get_type_hints(_TD, include_extras=True)
parsed_type_int = ParsedType(int)


def _check_parsed_type(parsed_type: ParsedType, expected: dict[str, Any]) -> None:
    for key, value in expected.items():
        assert getattr(parsed_type, key) == value


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
                "is_annotated": False,
                "is_required": False,
                "is_not_required": False,
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
                "is_annotated": False,
                "is_required": False,
                "is_not_required": False,
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
                "is_annotated": True,
                "is_required": False,
                "is_not_required": False,
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
                "is_annotated": True,
                "is_required": False,
                "is_not_required": False,
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
                "is_annotated": False,
                "is_required": True,
                "is_not_required": False,
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
                "is_annotated": False,
                "is_required": True,
                "is_not_required": False,
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
                "is_annotated": False,
                "is_required": False,
                "is_not_required": True,
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
                "is_annotated": False,
                "is_required": False,
                "is_not_required": True,
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
                "is_annotated": True,
                "is_required": True,
                "is_not_required": False,
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
                "is_annotated": True,
                "is_required": True,
                "is_not_required": False,
                "safe_generic_origin": List,
                "inner_types": (parsed_type_int,),
            },
        ),
    ],
)
def test_parsed_type_from_annotation(annotation: Any, expected: dict[str, Any]) -> None:
    """Test ParsedType.from_annotation."""
    _check_parsed_type(ParsedType(annotation), expected)


def test_parsed_type_from_union_annotation() -> None:
    """Test ParsedType.from_annotation for Union."""
    annotation = Union[int, List[int]]
    expected = {
        "raw": annotation,
        "annotation": annotation,
        "origin": Union,
        "args": (int, List[int]),
        "metadata": (),
        "is_annotated": False,
        "is_required": False,
        "is_not_required": False,
        "safe_generic_origin": Union,
        "inner_types": (ParsedType(int), ParsedType(List[int])),
    }
    _check_parsed_type(ParsedType(annotation), expected)


@pytest.mark.parametrize("value", ["int", ForwardRef("int")])
def test_parsed_type_is_forward_ref_predicate(value: Any) -> None:
    """Test ParsedType with ForwardRef."""
    parsed_type = ParsedType(value)
    assert parsed_type.is_forward_ref is True
    assert parsed_type.annotation == value
    assert parsed_type.origin is None
    assert parsed_type.args == ()
    assert parsed_type.metadata == ()
    assert parsed_type.is_annotated is False
    assert parsed_type.is_required is False
    assert parsed_type.is_not_required is False
    assert parsed_type.safe_generic_origin is None
    assert parsed_type.inner_types == ()


def test_parsed_type_is_type_var_predicate() -> None:
    """Test ParsedType.is_type_var."""
    assert ParsedType(int).is_type_var is False
    assert ParsedType(T).is_type_var is True
    assert ParsedType(Union[int, T]).is_type_var is False


def test_parsed_type_is_union_predicate() -> None:
    """Test ParsedType.is_union."""
    assert ParsedType(int).is_union is False
    assert ParsedType(Optional[int]).is_union is True
    assert ParsedType(Union[int, None]).is_union is True
    assert ParsedType(Union[int, str]).is_union is True


def test_parsed_type_is_optional_predicate() -> None:
    """Test ParsedType.is_optional."""
    assert ParsedType(int).is_optional is False
    assert ParsedType(Optional[int]).is_optional is True
    assert ParsedType(Union[int, None]).is_optional is True
    assert ParsedType(Union[int, None, str]).is_optional is True
    assert ParsedType(Union[int, str]).is_optional is False


def test_parsed_type_is_subclass_of() -> None:
    """Test ParsedType.is_type_of."""
    assert ParsedType(bool).is_subclass_of(int) is True
    assert ParsedType(bool).is_subclass_of(str) is False
    assert ParsedType(Union[int, str]).is_subclass_of(int) is False
    assert ParsedType(List[int]).is_subclass_of(list) is True
    assert ParsedType(List[int]).is_subclass_of(int) is False
    assert ParsedType(Optional[int]).is_subclass_of(int) is False


def test_parsed_type_has_inner_subclass_of() -> None:
    """Test ParsedType.has_type_of."""
    assert ParsedType(List[int]).has_inner_subclass_of(int) is True
    assert ParsedType(List[int]).has_inner_subclass_of(str) is False
    assert ParsedType(List[Union[int, str]]).has_inner_subclass_of(int) is False


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


def test_parsed_type_equality() -> None:
    assert ParsedType(int) == ParsedType(int)
    assert ParsedType(int) == ParsedType(Annotated[int, "meta"])
    assert ParsedType(int) != int
    assert ParsedType(List[int]) == ParsedType(List[int])
    assert ParsedType(List[int]) != ParsedType(List[str])
    assert ParsedType(List[str]) != ParsedType(Tuple[str])
    assert ParsedType(Optional[str]) == ParsedType(Union[str, None])


@pytest.mark.parametrize(
    ("annotation", "default", "expected"),
    [
        (int, None, RequestEncodingType.JSON),
        (int, Body(media_type=RequestEncodingType.MESSAGEPACK), RequestEncodingType.MESSAGEPACK),
        (Annotated[int, Body(media_type=RequestEncodingType.MESSAGEPACK)], None, RequestEncodingType.MESSAGEPACK),
    ],
)
def test_infer_request_encoding_type_from_parameter(
    annotation: Any, default: Any, expected: RequestEncodingType
) -> None:
    """Test infer_request_encoding_type_from_parameter."""
    assert infer_request_encoding_from_parameter(ParsedParameter("foo", default, ParsedType(annotation))) == expected
