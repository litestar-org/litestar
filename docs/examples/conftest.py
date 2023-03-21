from typing import TYPE_CHECKING, Generator

from freezegun import freeze_time

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

from typing import cast

import pytest


@pytest.fixture()
def frozen_datetime() -> Generator["FrozenDateTimeFactory", None, None]:
    with freeze_time() as frozen:
        yield cast("FrozenDateTimeFactory", frozen)
