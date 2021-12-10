from typing import Any, Callable

import pytest
from starlette.testclient import TestClient

from starlite.app import Starlite


@pytest.fixture(scope="function")
def create_test_client() -> Callable[[Any], TestClient]:
    def inner(routes: Any) -> TestClient:
        app = Starlite(route_handlers=routes if isinstance(routes, list) else [routes])
        return TestClient(app=app)

    return inner
