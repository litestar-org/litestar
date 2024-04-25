from __future__ import annotations

import pytest

from litestar.utils.empty import Empty, EmptyValueError, value_or_raise


def test_value_or_raise_empty() -> None:
    with pytest.raises(EmptyValueError):
        value_or_raise(Empty)


def test_value_or_raise_value() -> None:
    assert value_or_raise(1) == 1
