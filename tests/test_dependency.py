from typing import Any, Dict, Generator, Optional

import pytest
from starlette.testclient import TestClient

from starlite import Dependency, Provide, Starlite, get
from starlite.exceptions import ImproperlyConfiguredException
from starlite.testing import create_test_client


@pytest.fixture
def client(request: Any) -> Generator[TestClient, None, None]:
    @get("/optional")
    def optional_dep_handler(value: Optional[int] = request.param) -> Dict[str, Optional[int]]:
        return {"value": value}

    @get("/non-optional")
    def non_optional_dep_handler(value: int = request.param) -> Dict[str, Optional[int]]:
        return {"value": value}

    with create_test_client(route_handlers=[optional_dep_handler, non_optional_dep_handler]) as client:
        yield client


def test_is_dependency_inserted_into_field_extra() -> None:
    assert Dependency().extra["is_dependency"] is True


@pytest.mark.parametrize(
    "client, exp",
    [
        (Dependency(), None),
        (Dependency(default=None), None),
        (Dependency(default=13), 13),
    ],
    indirect=["client"],
)
def test_dependency_defaults(client: TestClient, exp: Optional[int]) -> None:
    resp = client.get("/optional")
    assert resp.json() == {"value": exp}


@pytest.mark.parametrize("client", [Dependency(default=13)], indirect=True)
def test_dependency_non_optional_with_default(client: TestClient) -> None:
    resp = client.get("/non-optional")
    assert resp.json() == {"value": 13}


def test_no_default_dependency_provided() -> None:
    @get(dependencies={"value": Provide(lambda: 13)})
    def test(value: int = Dependency()) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[test]) as client:
        resp = client.get("/")
    assert resp.json() == {"value": 13}


@pytest.mark.xfail
def test_dependency_not_provided_and_no_default() -> None:
    @get()
    def test(value: int = Dependency()) -> Dict[str, int]:
        return {"value": value}

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[test])
