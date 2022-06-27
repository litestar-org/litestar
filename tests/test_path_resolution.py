from typing import Any, Callable, Optional
from uuid import uuid4

import pytest
from starlette.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from typing_extensions import Type

from starlite import Controller, HTTPRouteHandler, MediaType, delete, get
from starlite.testing import create_test_client
from tests import Person, PersonFactory


@delete()
def root_delete_handler() -> None:
    return None


@pytest.mark.parametrize(
    "request_path, router_path",
    [
        [f"/path/1/2/sub/{str(uuid4())}", "/path/{first:int}/{second:str}/sub/{third:uuid}"],
        [f"/path/1/2/sub/{str(uuid4())}/", "/path/{first:int}/{second:str}/sub/{third:uuid}/"],
        ["/", "/"],
        ["", ""],
    ],
)
def test_path_parsing_and_matching(request_path: str, router_path: str) -> None:
    @get(path=router_path)
    def test_method() -> None:
        return None

    with create_test_client(test_method) as client:
        response = client.get(request_path)
        assert response.status_code == HTTP_200_OK


def test_path_parsing_with_ambiguous_paths() -> None:
    @get(path="/{path_param:int}", media_type=MediaType.TEXT)
    def path_param(path_param: int) -> str:
        return str(path_param)

    @get(path="/query_param", media_type=MediaType.TEXT)
    def query_param(value: int) -> str:
        return str(value)

    @get(path="/mixed/{path_param:int}", media_type=MediaType.TEXT)
    def mixed_params(path_param: int, value: int) -> str:
        return str(path_param + value)

    with create_test_client([path_param, query_param, mixed_params]) as client:
        response = client.get("/1")
        assert response.status_code == HTTP_200_OK
        response = client.get("/query_param?value=1")
        assert response.status_code == HTTP_200_OK
        response = client.get("/mixed/1/?value=1")
        assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize(
    "decorator, test_path, decorator_path, delete_handler",
    [
        (get, "", "/something", None),
        (get, "/", "/something", None),
        (get, "", "/", None),
        (get, "/", "/", None),
        (get, "", "", None),
        (get, "/", "", None),
        (get, "", "/something", root_delete_handler),
        (get, "/", "/something", root_delete_handler),
        (get, "", "/", root_delete_handler),
        (get, "/", "/", root_delete_handler),
        (get, "", "", root_delete_handler),
        (get, "/", "", root_delete_handler),
    ],
)
def test_root_route_handler(
    decorator: Type[HTTPRouteHandler], test_path: str, decorator_path: str, delete_handler: Optional[Callable]
) -> None:
    person_instance = PersonFactory.build()

    class MyController(Controller):
        path = test_path

        @decorator(path=decorator_path)
        def test_method(self) -> Person:
            return person_instance

    with create_test_client([MyController, delete_handler] if delete_handler else MyController) as client:
        response = client.get(decorator_path or test_path)
        assert response.status_code == HTTP_200_OK
        assert response.json() == person_instance.dict()
        if delete_handler:
            delete_response = client.delete("/")
            assert delete_response.status_code == HTTP_204_NO_CONTENT


def test_handler_multi_paths() -> None:
    @get(path=["/", "/something", "/{some_id:int}", "/something/{some_id:int}"], media_type=MediaType.TEXT)
    def handler_fn(some_id: int = 1) -> str:
        assert some_id
        return str(some_id)

    with create_test_client(handler_fn) as client:
        first_response = client.get("/")
        assert first_response.status_code == HTTP_200_OK
        assert first_response.text == "1"
        second_response = client.get("/2")
        assert second_response.status_code == HTTP_200_OK
        assert second_response.text == "2"
        third_response = client.get("/something")
        assert third_response.status_code == HTTP_200_OK
        assert third_response.text == "1"
        fourth_response = client.get("/something/2")
        assert fourth_response.status_code == HTTP_200_OK
        assert fourth_response.text == "2"


@pytest.mark.parametrize(
    "handler_path, request_path, expected_status_code",
    [
        ("/sub-path", "/", HTTP_404_NOT_FOUND),
        ("/sub/path", "/sub-path", HTTP_404_NOT_FOUND),
        ("/sub/path", "/sub", HTTP_404_NOT_FOUND),
        ("/sub/path/{path_param:int}", "/sub/path", HTTP_404_NOT_FOUND),
        ("/sub/path/{path_param:int}", "/sub/path/abcd", HTTP_400_BAD_REQUEST),
        ("/sub/path/{path_param:uuid}", "/sub/path/100", HTTP_400_BAD_REQUEST),
        ("/sub/path/{path_param:float}", "/sub/path/abcd", HTTP_400_BAD_REQUEST),
    ],
)
def test_path_validation(handler_path: str, request_path: str, expected_status_code: int) -> None:
    @get(handler_path)
    def handler_fn(**kwargs: Any) -> None:
        ...

    with create_test_client(handler_fn) as client:
        response = client.get(request_path)
        assert response.status_code == expected_status_code
