import pytest
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from starlite import Controller, MediaType, create_test_client, delete, get
from tests import Person, PersonFactory


@delete()
def root_delete_handler() -> None:
    return None


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
def test_root_route_handler(decorator, test_path, decorator_path, delete_handler):
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


def test_handler_multi_paths():
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
