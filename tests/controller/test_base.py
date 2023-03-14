from typing import Any, Type, Union

import pytest
from pydantic import BaseModel

from starlite import (
    Controller,
    HttpMethod,
    Response,
    Starlite,
    delete,
    get,
    patch,
    post,
    put,
    websocket,
)
from starlite.connection import WebSocket
from starlite.exceptions import ImproperlyConfiguredException
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from starlite.testing import create_test_client
from tests import Person, PersonFactory


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code, return_value, return_annotation",
    [
        (
            get,
            HttpMethod.GET,
            HTTP_200_OK,
            Response(content=PersonFactory.build()),
            Response[Person],
        ),
        (get, HttpMethod.GET, HTTP_200_OK, PersonFactory.build(), Person),
        (post, HttpMethod.POST, HTTP_201_CREATED, PersonFactory.build(), Person),
        (put, HttpMethod.PUT, HTTP_200_OK, PersonFactory.build(), Person),
        (patch, HttpMethod.PATCH, HTTP_200_OK, PersonFactory.build(), Person),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT, None, None),
    ],
)
async def test_controller_http_method(
    decorator: Union[Type[get], Type[post], Type[put], Type[patch], Type[delete]],
    http_method: HttpMethod,
    expected_status_code: int,
    return_value: Any,
    return_annotation: Any,
) -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self) -> return_annotation:
            return return_value

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code
        if return_value:
            assert response.json() == return_value.dict() if isinstance(return_value, BaseModel) else return_value


def test_controller_with_websocket_handler() -> None:
    test_path = "/person"

    class MyController(Controller):
        path = test_path

        @get()
        def get_person(self) -> Person:
            return PersonFactory.build()

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


def test_controller_validation() -> None:
    class BuggyController(Controller):
        path: str = "/ctrl"

        @get()
        async def handle_get(self) -> str:
            return "Hello World"

        @get()
        async def handle_get2(self) -> str:
            return "Hello World"

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[BuggyController])
