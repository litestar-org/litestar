from typing import Any, Dict, List, Optional

import pytest

from starlite import Controller, Starlite, get
from starlite.di import Provide
from starlite.exceptions import ImproperlyConfiguredException
from starlite.params import Dependency
from starlite.status_codes import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR
from starlite.testing import create_test_client


@pytest.mark.parametrize(
    "dependency, expected",
    [
        (Dependency(), None),
        (Dependency(default=None), None),
        (Dependency(default=13), 13),
    ],
)
def test_dependency_defaults(dependency: Any, expected: Optional[int]) -> None:
    @get("/")
    def handler(value: Optional[int] = dependency) -> Dict[str, Optional[int]]:
        return {"value": value}

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.get("/")
        assert resp.json() == {"value": expected}


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
    """Ensures that we don't only consider the handler's dependencies when checking that an explicit non-optional
    dependency has been provided.
    """

    class C(Controller):
        path = ""
        dependencies = {"value": Provide(lambda: 13)}

        @get()
        def test(self, value: int = Dependency()) -> Dict[str, int]:
            return {"value": value}

    with create_test_client(route_handlers=[C]) as client:
        resp = client.get("/")
    assert resp.json() == {"value": 13}


def test_dependency_skip_validation() -> None:
    @get("/validated")
    def validated(value: int = Dependency()) -> Dict[str, int]:
        return {"value": value}

    @get("/skipped")
    def skipped(value: int = Dependency(skip_validation=True)) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(
        route_handlers=[validated, skipped], dependencies={"value": Provide(lambda: "str")}
    ) as client:
        validated_resp = client.get("/validated")
        assert validated_resp.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        skipped_resp = client.get("/skipped")
        assert skipped_resp.status_code == HTTP_200_OK
        assert skipped_resp.json() == {"value": "str"}


def test_dependency_skip_validation_with_default_value() -> None:
    @get("/skipped")
    def skipped(value: int = Dependency(default=1, skip_validation=True)) -> Dict[str, int]:
        return {"value": value}

    with create_test_client(route_handlers=[skipped]) as client:
        skipped_resp = client.get("/skipped")
        assert skipped_resp.status_code == HTTP_200_OK
        assert skipped_resp.json() == {"value": 1}


def test_nested_sequence_dependency() -> None:
    class Obj:
        def __init__(self, seq: List[str]) -> None:
            self.seq = seq

    def provides_obj(seq: List[str]) -> Obj:
        return Obj(seq)

    @get("/obj")
    def get_obj(obj: Obj) -> List[str]:
        return obj.seq

    @get("/seq")
    def get_seq(seq: List[str]) -> List[str]:
        return seq

    with create_test_client(
        route_handlers=[get_obj, get_seq],
        dependencies={"obj": Provide(provides_obj)},
    ) as client:
        seq = ["a", "b", "c"]
        resp = client.get("/seq", params={"seq": seq})
        assert resp.json() == ["a", "b", "c"]
        resp = client.get("/obj", params={"seq": seq})
        assert resp.json() == ["a", "b", "c"]
