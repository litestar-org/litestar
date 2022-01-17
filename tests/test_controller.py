from typing import List, Optional

import pytest
from pydantic import BaseModel, Field
from pydantic_factories import ModelFactory
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from starlite import (
    Controller,
    HttpMethod,
    ImproperlyConfiguredException,
    Router,
    create_test_client,
    delete,
    get,
    patch,
    post,
    put,
    websocket,
)
from starlite.request import Request, WebSocket
from tests import Person, PersonFactory


class QueryParams(BaseModel):
    first: str
    second: List[str] = Field(min_items=3)
    third: Optional[int]


class QueryParamsFactory(ModelFactory):
    __model__ = QueryParams


person_instance = PersonFactory.build()


def test_controller_raises_exception_when_base_path_not_set():
    class MyController(Controller):
        pass

    with pytest.raises(ImproperlyConfiguredException):
        MyController(owner=Router(path="", route_handlers=[]))


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
def test_controller_http_method(decorator, http_method, expected_status_code):
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self) -> Person:
            return person_instance

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code
        assert response.json() == person_instance.dict()


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
def test_path_params(decorator, http_method, expected_status_code):
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
def test_query_params(decorator, http_method, expected_status_code):
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
def test_header_params(decorator, http_method, expected_status_code):
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
def test_request(decorator, http_method, expected_status_code):
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self, request: Request) -> None:
            assert isinstance(request, Request)

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code


def test_defining_data_for_get_handler_raises_exception():
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @get()
        def test_method(self, data: Person) -> None:
            assert data == person_instance

    with create_test_client(MyController) as client:
        response = client.get(test_path)
        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code",
    [
        (post, HttpMethod.POST, HTTP_201_CREATED),
        (put, HttpMethod.PUT, HTTP_200_OK),
        (patch, HttpMethod.PATCH, HTTP_200_OK),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT),
    ],
)
def test_data_using_model(decorator, http_method, expected_status_code):
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
def test_data_using_list_of_models(decorator, http_method, expected_status_code):
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


def test_controller_with_websocket_handler():
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @get()
        def get_person(self) -> Person:
            ...

        @websocket(path="/socket")
        async def ws(self, socket: WebSocket) -> None:
            await socket.accept()
            await socket.send_json({"data": "123"})
            await socket.close()

    client = create_test_client(route_handlers=MyController)

    with client.websocket_connect(test_path + "/socket") as ws:
        ws.send_json({"data": "123"})
        data = ws.receive_json()
        assert data


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
def test_controller_empty_path(decorator, http_method, expected_status_code):
    test_path = ""

    class MyController(Controller):
        path = test_path

        @decorator(path="/")
        def test_method(self) -> Person:
            return person_instance

    with pytest.warns(UserWarning), create_test_client(MyController) as client:
        response = client.request(http_method, "/")
        assert response.status_code == expected_status_code
        assert response.json() == person_instance.dict()
