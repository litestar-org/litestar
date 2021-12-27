from asyncio import sleep
from typing import Any, Dict

import pytest
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from starlite import (
    Controller,
    ImproperlyConfiguredException,
    Provide,
    Starlite,
    create_test_client,
    get,
)
from starlite.request import Request


def router_first_dependency():
    return True


async def router_second_dependency():
    await sleep(0.1)
    return False


def controller_first_dependency(headers: Dict[str, Any]):
    assert headers
    return dict()


async def controller_second_dependency(request: Request):
    assert request
    await sleep(0.1)
    return dict()


def local_method_first_dependency(query_param: int):
    assert isinstance(query_param, int)
    return query_param


def local_method_second_dependency(path_param: str):
    assert isinstance(path_param, str)
    return path_param


test_path = "/test"


class FirstController(Controller):
    path = test_path
    dependencies = {"first": Provide(controller_first_dependency), "second": Provide(controller_second_dependency)}

    @get(
        path="/{path_param:str}",
        dependencies={
            "first": Provide(local_method_first_dependency),
        },
    )
    def test_method(self, first: int, second: dict, third: bool) -> None:
        assert isinstance(first, int)
        assert isinstance(second, dict)
        assert third is False


def test_controller_dependency_injection():
    with create_test_client(
        FirstController,
        dependencies={
            "second": Provide(router_first_dependency),
            "third": Provide(router_second_dependency),
        },
    ) as client:
        response = client.get(f"{test_path}/abcdef?query_param=12345")
        assert response.status_code == HTTP_200_OK


def test_function_dependency_injection():
    @get(
        path=test_path + "/{path_param:str}",
        dependencies={
            "first": Provide(local_method_first_dependency),
            "third": Provide(local_method_second_dependency),
        },
    )
    def test_function(first: int, second: bool, third: str) -> None:
        assert isinstance(first, int)
        assert second is False
        assert isinstance(third, str)

    with create_test_client(
        test_function,
        dependencies={
            "first": Provide(router_first_dependency),
            "second": Provide(router_second_dependency),
        },
    ) as client:
        response = client.get(f"{test_path}/abcdef?query_param=12345")
        assert response.status_code == HTTP_200_OK


def test_dependency_isolation():
    class SecondController(Controller):
        path = "/second"

        @get()
        def test_method(self, first: dict) -> None:
            pass

    with create_test_client([FirstController, SecondController]) as client:
        response = client.get("/second")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_dependency_validation():
    @get(
        path=test_path + "/{path_param:int}",
        dependencies={
            "first": Provide(local_method_first_dependency),
            "second": Provide(local_method_second_dependency),
        },
    )
    def test_function(first: int, second: str, third: int) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(
            route_handlers=[test_function],
            dependencies={
                "third": Provide(local_method_first_dependency),
            },
        )
