from typing import Any, Dict, Optional

import pytest

from starlite import Controller, Dependency, Provide, Starlite, get
from starlite.constants import EXTRA_KEY_IS_DEPENDENCY
from starlite.exceptions import ImproperlyConfiguredException
from starlite.testing import create_test_client


def test_is_dependency_inserted_into_field_extra() -> None:
    assert Dependency().extra[EXTRA_KEY_IS_DEPENDENCY] is True


@pytest.mark.parametrize(
    "field_info, exp",
    [
        (Dependency(), None),
        (Dependency(default=None), None),
        (Dependency(default=13), 13),
    ],
)
def test_dependency_defaults(field_info: Any, exp: Optional[int]) -> None:
    @get("/")
    def handler(value: Optional[int] = field_info) -> Dict[str, Optional[int]]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.json() == {"value": exp}


def test_non_optional_with_default() -> None:
    @get("/")
    def handler(value: int = Dependency(default=13)) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.json() == {"value": 13}


def test_no_default_dependency_provided() -> None:
    @get(dependencies={"value": Provide(lambda: 13)})
    def test(value: int = Dependency()) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[test]) as client:
        resp = client.get("/")
    assert resp.json() == {"value": 13}


def test_dependency_not_provided_and_no_default() -> None:
    @get()
    def test(value: int = Dependency()) -> Dict[str, int]:
        return {"value": value}

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[test])


def test_dependency_provided_on_controller() -> None:
    """Ensures that we don't only consider the handler's dependencies when
    checking that an explicit non-optional dependency has been provided."""

    class C(Controller):
        path = ""
        dependencies = {"value": Provide(lambda: 13)}

        @get()
        def test(self, value: int = Dependency()) -> Dict[str, int]:
            return {"value": value}

    with create_test_client(route_handlers=[C]) as client:
        resp = client.get("/")
    assert resp.json() == {"value": 13}
