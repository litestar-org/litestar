# ruff: noqa: UP007
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from msgspec import Struct

from litestar.dto.factory._backends.msgspec.utils import _build_struct_from_model

if TYPE_CHECKING:
    from typing import Union


@dataclass
class FooDC:
    foo: str


@dataclass
class BarDC:
    bar: str


@dataclass
class FooBarDC:
    baz: Union[FooDC, BarDC]


class FooStruct(Struct):
    foo: str


class BarStruct(Struct):
    bar: str


class FooBarStruct(Struct):
    baz: Union[FooStruct, BarStruct]


def test_build_struct_from_model_with_non_optional_nested_union() -> None:
    model = FooBarDC(baz=BarDC(bar="bar"))
    struct = _build_struct_from_model(model, FooBarStruct, {})
    assert isinstance(struct.baz, BarStruct)
