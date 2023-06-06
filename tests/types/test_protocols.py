from __future__ import annotations

from typing import Any

import pytest

from litestar.types.protocols import InstantiableCollection


@pytest.mark.parametrize(
    "collection,expected",
    [
        (list, True),
        (tuple, True),
        (set, True),
        (frozenset, True),
        (str, True),
        (dict, True),
        (int, False),
        (float, False),
        (bool, False),
    ],
)
def test_homogenous_instantiable_collection(collection: type[Any], expected: bool) -> None:
    assert issubclass(collection, InstantiableCollection) == expected
