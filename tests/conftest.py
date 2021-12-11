from typing import Any, Callable, Dict, Optional

import pytest
from starlette.testclient import TestClient

from starlite import Inject
from starlite.app import Starlite


@pytest.fixture(scope="function")
def create_test_client() -> Callable[[Any], TestClient]:
    def inner(routes: Any, dependencies: Optional[Dict[str, Inject]] = None) -> TestClient:
        app = Starlite(route_handlers=routes if isinstance(routes, list) else [routes], dependencies=dependencies)
        return TestClient(app=app)

    return inner
