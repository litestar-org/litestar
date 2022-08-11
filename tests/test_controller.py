from typing import Any, NoReturn, Type, Union

import pytest
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from starlite import Controller, HttpMethod, delete, get, patch, post, put, websocket
from starlite.connection import WebSocket
from starlite.testing import create_test_client
from tests import Person, PersonFactory


@pytest.mark.parametrize(
    "decorator, http_method, expected_status_code, return_annotation",
    [
        (get, HttpMethod.GET, HTTP_200_OK, Person),
        (post, HttpMethod.POST, HTTP_201_CREATED, Person),
        (put, HttpMethod.PUT, HTTP_200_OK, Person),
        (patch, HttpMethod.PATCH, HTTP_200_OK, Person),
        (delete, HttpMethod.DELETE, HTTP_204_NO_CONTENT, NoReturn),
    ],
)
def test_controller_http_method(
    decorator: Union[Type[get], Type[post], Type[put], Type[patch], Type[delete]],
    http_method: HttpMethod,
    expected_status_code: int,
    return_annotation: Any,
) -> None:
    test_path = "/person"
    person_instance = PersonFactory.build()

    class MyController(Controller):
        path = test_path

        @decorator()
        def test_method(self) -> return_annotation:  # type: ignore[valid-type]
            return person_instance

    with create_test_client(MyController) as client:
        response = client.request(http_method, test_path)
        assert response.status_code == expected_status_code
        assert response.json() == person_instance.dict()


def test_controller_with_websocket_handler() -> None:
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
