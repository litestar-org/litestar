from typing import Any, List, Optional, cast

import pytest
from pydantic import BaseModel, Field
from pydantic_factories import ModelFactory
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite import (
    Controller,
    HttpMethod,
    MediaType,
    Request,
    State,
    delete,
    get,
    patch,
    post,
    put,
)
from starlite.testing import create_test_client
from tests import Person, PersonFactory


def test_application_state_injection() -> None:
    @get("/", media_type=MediaType.TEXT)
    def route_handler(state: State) -> str:
        assert state
        state.called = True  # this should not modify the app state
        return cast(str, state.msg)  # this shows injection worked

    with create_test_client(route_handler) as client:
        client.app.state.msg = "hello"
        client.app.state.called = False
        response = client.get("/")
        assert response.text == "hello"
        assert not client.app.state.called


class QueryParams(BaseModel):
    first: str
    second: List[str] = Field(min_items=3)
    third: Optional[int]


class QueryParamsFactory(ModelFactory):
    __model__ = QueryParams


person_instance = PersonFactory.build()


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_data_using_model(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, data: Person) -> None:
            assert data == person_instance

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=person_instance.dict())
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_data_using_list_of_models(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    people = PersonFactory.batch(size=5)

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, data: List[Person]) -> None:
            assert data == people

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, json=[p.dict() for p in people])
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_path_params(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator(path="/{person_id:str}")
        def test_method(self, person_id: str) -> None:
            assert person_id == person_instance.id
            return None

    with create_test_client(MyController) as client:
        response = client.request(http_method, f"{test_path}/{person_instance.id}")
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_query_params(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    query_params_instance = QueryParamsFactory.build()

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, first: str, second: List[str], third: Optional[int] = None) -> None:
            assert first == query_params_instance.first
            assert second == query_params_instance.second
            assert third == query_params_instance.third
            return None

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, params=query_params_instance.dict())
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_header_params(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    request_headers = {
        "application-type": "web",
        "site": "www.example.com",
        "user-agent": "some-thing",
        "accept": "*/*",
    }

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, headers: dict) -> None:
            for key, value in request_headers.items():
                assert headers[key] == value

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path, headers=request_headers)
        assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (get, HttpMethod.GET, HTTP_200_OK),
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_request(decorator: Any, http_method: Any, expected_status_code: Any) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, request: Request) -> None:
            assert isinstance(request, Request)

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code
