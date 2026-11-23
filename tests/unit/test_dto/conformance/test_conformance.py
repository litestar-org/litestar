from typing import Any

import pytest

from tests.unit.test_dto.conformance.features import Direction, Feature
from tests.unit.test_dto.conformance.harness import cell_ids, find_gap
from tests.unit.test_dto.conformance.known_gaps import KNOWN_GAPS
from tests.unit.test_dto.conformance.models import Library


def _cells() -> list[Any]:
    return [
        pytest.param(feature, library, direction, id=f"{feature.id}-{library}-{direction}")
        for feature, library, direction in cell_ids()
    ]


@pytest.mark.parametrize(("feature", "library", "direction"), _cells())
def test_cell(feature: Feature, library: Library, direction: Direction) -> None:
    cell = f"{feature.id}-{library}-{direction}"
    known = KNOWN_GAPS.get(cell)
    gap = find_gap(feature, library, direction)
    assert gap == known
    if known is not None:
        pytest.xfail(known)


def test_known_gaps_name_existing_cells() -> None:
    cells = {f"{feature.id}-{library}-{direction}" for feature, library, direction in cell_ids()}
    assert set(KNOWN_GAPS) <= cells
