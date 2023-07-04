# ruff: noqa: UP006,UP007

from __future__ import annotations

import inspect
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
from litestar.typing import FieldDefinition
from litestar.utils.signature import (
    ParsedSignature,
    get_fn_type_hints,
    infer_request_encoding_from_field_definition,
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
field_definition_int = FieldDefinition.from_annotation(int)


def _check_field_definition(field_definition: FieldDefinition, expected: dict[str, Any]) -> None:
    for key, value in expected.items():
        assert getattr(field_definition, key) == value


def test_field_definition_from_parameter() -> None:
    """Test FieldDefinition."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    parsed_param = FieldDefinition.from_parameter(param, {"foo": int})
    assert parsed_param.name == "foo"
    assert parsed_param.default is Empty
    assert parsed_param.annotation is int


def test_field_definition_from_parameter_raises_improperly_configured_if_no_annotation() -> None:
    """Test FieldDefinition raises ImproperlyConfigured if no annotation."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD)
    with pytest.raises(ImproperlyConfiguredException):
        FieldDefinition.from_parameter(param, {})


def test_field_definition_from_parameter_has_default_predicate() -> None:
    """Test FieldDefinition.has_default."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    parsed_param = FieldDefinition.from_parameter(param, {"foo": int})
    assert parsed_param.has_default is False

    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int, default=42)
    parsed_param = FieldDefinition.from_parameter(param, {"foo": int})
    assert parsed_param.has_default is True


def test_field_definition_from_parameter_annotation_property() -> None:
    """Test FieldDefinition.annotation."""
    param = Parameter("foo", Parameter.POSITIONAL_OR_KEYWORD, annotation=int)
    parsed_param = FieldDefinition.from_parameter(param, {"foo": int})
    assert parsed_param.annotation is int
    assert parsed_param.annotation is int


def test_parsed_signature() -> None:
    """Test ParsedSignature."""

    def fn(foo: int, bar: Optional[List[int]] = None) -> None:
        ...

    parsed_sig = ParsedSignature.from_fn(fn, get_fn_type_hints(fn))
    assert parsed_sig.return_type.annotation is NoneType
    assert parsed_sig.parameters["foo"].annotation is int
    assert parsed_sig.parameters["bar"].args == (List[int], NoneType)
    assert parsed_sig.parameters["bar"].annotation == Union[List[int], NoneType]
    assert parsed_sig.parameters["bar"].default is Empty
    assert parsed_sig.original_signature == inspect.signature(fn)


@pytest.mark.parametrize(
    ("annotation", "default", "expected"),
    [
        (int, None, RequestEncodingType.JSON),
        (int, Body(media_type=RequestEncodingType.MESSAGEPACK), RequestEncodingType.MESSAGEPACK),
        (Annotated[int, Body(media_type=RequestEncodingType.MESSAGEPACK)], None, RequestEncodingType.MESSAGEPACK),
    ],
)
def xtest_infer_request_encoding_type_from_parameter(
    annotation: Any, default: Any, expected: RequestEncodingType
) -> None:
    """Test infer_request_encoding_type_from_parameter."""
    assert (
        infer_request_encoding_from_field_definition(
            FieldDefinition.from_kwarg(name="foo", default=default, annotation=annotation)
        )
        == expected
    )
