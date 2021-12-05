from typing import Callable, List, Union

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient


@pytest.fixture(scope="function")
def create_test_client() -> Callable[[Union[Route, List[Route]]], TestClient]:
    def inner(routes: Union[Route, List[Route]]) -> TestClient:
        app = Starlette(routes=routes if isinstance(routes, list) else [routes])
        return TestClient(app=app)

    return inner
