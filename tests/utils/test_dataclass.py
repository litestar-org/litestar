from __future__ import annotations

from dataclasses import dataclass

import pytest

from litestar.types import DataclassProtocol, Empty, EmptyType
from litestar.utils.dataclass import (
    extract_dataclass_fields,
    extract_dataclass_items,
    simple_asdict,
)
from litestar.utils.predicates import (
    is_dataclass_class,
    is_dataclass_instance,
)


def test_extract_dataclass_fields_exclude_none() -> None:
    """Test extract_dataclass_fields with exclude_none."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str | None = None

    assert extract_dataclass_fields(Foo(), exclude_none=True) == ()


def test_extract_dataclass_fields_exclude_empty() -> None:
    """Test extract_dataclass_fields with exclude_empty."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str | EmptyType = Empty

    assert extract_dataclass_fields(Foo(), exclude_empty=True) == ()


def test_extract_dataclass_fields_include() -> None:
    """Test extract_dataclass_items with include."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"
        baz: str = "baz"

    fields = extract_dataclass_fields(Foo(), include={"bar"})
    assert len(fields) == 1
    assert fields[0].name == "bar"
    assert fields[0].default == "bar"


def test_extract_dataclass_fields_exclude() -> None:
    """Test extract_dataclass_items with exclude."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"
        baz: str = "baz"

    fields = extract_dataclass_fields(Foo(), exclude={"bar"})
    assert len(fields) == 1
    assert fields[0].name == "baz"
    assert fields[0].default == "baz"


def test_extract_dataclass_fields_raises_for_common_include_exclude() -> None:
    """Test extract_dataclass_items raises for common include and exclude."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"

    with pytest.raises(ValueError):
        extract_dataclass_fields(Foo(), include={"bar"}, exclude={"bar"})


def test_extract_dataclass_items_returns_name_value_pairs() -> None:
    """Test extract_dataclass_items returns name, value pairs."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"
        baz: str = "baz"

    assert extract_dataclass_items(Foo()) == (("bar", "bar"), ("baz", "baz"))


def test_simple_asdict_returns_dict() -> None:
    """Test simple_asdict returns a dict."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"
        baz: str = "baz"

    assert simple_asdict(Foo()) == {"bar": "bar", "baz": "baz"}


def test_simple_asdict_recursive() -> None:
    """Test simple_asdict recursive."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"
        baz: str = "baz"

    @dataclass
    class Bar:
        """A Bar model."""

        foo: Foo

    assert simple_asdict(Bar(foo=Foo())) == {"foo": {"bar": "bar", "baz": "baz"}}


def test_simple_asdict_does_not_recurse_into_collections() -> None:
    """Test simple_asdict does not recurse into collections."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"
        baz: str = "baz"

    @dataclass
    class Bar:
        """A Bar model."""

        foo: list[Foo]

    foo = Foo()

    assert simple_asdict(Bar(foo=[foo])) == {"foo": [foo]}


def test_isinstance_with_dataclass_protocol_returns_true_for_both_types_and_instances() -> None:
    """Test to demonstrate that dataclass types return True for isinstance checks against DataclassProtocol."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"

    assert isinstance(Foo(), DataclassProtocol)
    assert isinstance(Foo, DataclassProtocol)


def test_is_dataclass_instance() -> None:
    """is_dataclass_instance() should return True for instances and False for types."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"

    assert not is_dataclass_instance(Foo)
    assert is_dataclass_instance(Foo())


def test_is_dataclass_class() -> None:
    """is_dataclass_class() should return True for types and False for instances."""

    @dataclass
    class Foo:
        """A Foo model."""

        bar: str = "bar"

    assert is_dataclass_class(Foo)
    assert not is_dataclass_class(Foo())
