import pytest
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from starlite import Controller, create_test_client, delete, get
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
