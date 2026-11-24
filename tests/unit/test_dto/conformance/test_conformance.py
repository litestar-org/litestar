from typing import Any

import pytest

from tests.unit.test_dto.conformance.features import Direction, Feature
from tests.unit.test_dto.conformance.harness import cell_ids, find_gap
from tests.unit.test_dto.conformance.models import Library


def _cells() -> list[Any]:
    return [
        pytest.param(feature, library, direction, id=f"{feature.id}-{library}-{direction}")
        for feature, library, direction in cell_ids()
    ]


@pytest.mark.parametrize(("feature", "library", "direction"), _cells())
def test_cell(feature: Feature, library: Library, direction: Direction) -> None:
    if library == "py":
        pytest.importorskip("pydantic")

    assert find_gap(feature, library, direction) is None
