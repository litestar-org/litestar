from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from starlite.types import Empty
from starlite.utils.dataclass import asdict_filter_empty, simple_asdict, simple_asdict_filter_empty

if TYPE_CHECKING:
    from starlite.types import EmptyType


@dataclass
class Foo:
    bar: str = "baz"
    baz: int | EmptyType = Empty
    qux: list[str] = field(default_factory=lambda: ["quux", "quuz"])


@dataclass
class Bar:
    foo: Foo = field(default_factory=Foo)
    quux: list[Foo] = field(default_factory=lambda: [Foo(), Foo()])


def test_asdict_filter_empty() -> None:
    foo = Foo()
    assert asdict_filter_empty(foo) == {"bar": "baz", "qux": ["quux", "quuz"]}


def test_simple_asdict() -> None:
    bar = Bar()
    assert simple_asdict(bar) == {"foo": {"bar": "baz", "baz": Empty, "qux": ["quux", "quuz"]}, "quux": [Foo(), Foo()]}


def test_simple_asdict_filter_empty() -> None:
    bar = Bar()
    assert simple_asdict_filter_empty(bar) == {"foo": {"bar": "baz", "qux": ["quux", "quuz"]}, "quux": [Foo(), Foo()]}
