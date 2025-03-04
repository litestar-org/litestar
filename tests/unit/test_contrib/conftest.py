from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Callable


@pytest.fixture
def int_factory() -> Callable[[], int]:
    return lambda: 2
