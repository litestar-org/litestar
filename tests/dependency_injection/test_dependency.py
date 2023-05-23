from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

import pytest

from litestar import Controller, Litestar, get
from litestar.di import Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import Dependency
from litestar.status_codes import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import create_test_client


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
    @get(dependencies={"value": Provide(lambda: 13, sync_to_thread=False)})
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
        Litestar(route_handlers=[test])


def test_dependency_provided_on_controller() -> None:
    """Ensures that we don't only consider the handler's dependencies when checking that an explicit non-optional
    dependency has been provided.
    """

    class C(Controller):
        path = ""
        dependencies = {"value": Provide(lambda: 13, sync_to_thread=False)}

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
        route_handlers=[validated, skipped], dependencies={"value": Provide(lambda: "str", sync_to_thread=False)}
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

    async def provides_obj(seq: List[str]) -> Obj:
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


def sync_callable() -> float:
    return 0.1


async def async_callable() -> float:
    return 0.1


def sync_generator() -> Generator[float, None, None]:
    yield 0.1


async def async_generator() -> AsyncGenerator[float, None]:
    yield 0.1


@pytest.mark.parametrize(
    ("dep", "exp"),
    [(sync_callable, True), (async_callable, False), (sync_generator, True), (async_generator, False)],
)
def test_dependency_has_async_callable(dep: Any, exp: bool) -> None:
    assert Provide(dep).has_sync_callable is exp
