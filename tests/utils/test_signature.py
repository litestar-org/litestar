# ruff: noqa: UP006,UP007

from __future__ import annotations

import inspect
from dataclasses import dataclass
from inspect import Parameter
from typing import Any, List, Optional, TypeVar, Union

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
from litestar.typing import ParsedType
from litestar.utils.signature import (
    ParsedParameter,
    ParsedSignature,
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


def test_parsed_type_copy_with_dataclass_type() -> None:
    """This is a regression test for an issue that manifested using `ParsedParameter.copy_with()`.

    The actual issue was inside `utils.dataclass.simple_asdict()`, where `isinstance(value, DataclassProtocol)` would
    return `True` for both dataclass types and instances. This caused `simple_asdict()` to recurse for the dataclass
    type value, which was not correct.
    """

    @dataclass
    class Foo:
        bar: str

    parsed_parameter = ParsedParameter(name="foo", default=Empty, parsed_type=ParsedType(Foo)).copy_with(
        parsed_type=ParsedType(Union[Foo, None])
    )

    assert parsed_parameter.parsed_type == ParsedType(Union[Foo, None])
