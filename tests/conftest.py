from typing import Any, Callable

import pytest
from starlette.testclient import TestClient

from starlite.app import StarliteAPP
from starlite.utils import as_iterable


@pytest.fixture(scope="function")
def create_test_client() -> Callable[[Any], TestClient]:
    def inner(route_handlers: Any) -> TestClient:
        app = StarliteAPP(routes=list(as_iterable(route_handlers)))
        return TestClient(app=app)

    return inner
