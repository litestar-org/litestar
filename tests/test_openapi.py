from typing import List

from starlite import Controller, Partial, Starlite, delete, get, patch, put
from starlite.openapi import create_openapi_schema
from tests.utils import Person


class PersonController(Controller):
    path = "/person"

    @get()
    def get_persons(self) -> List[Person]:
        pass

    @get(path="/{person_id:str}")
    def get_person_by_id(self, person_id: str) -> Person:
        pass

    @patch(path="/{person_id:str}")
    def partial_update_person(self, person_id: str, data: Partial[Person]) -> Person:
        pass

    @put(path="/{person_id:str}")
    def update_person(self, person_id: str, data: Person) -> Person:
        pass

    @delete(path="/{person_id:str}")
    def delete_person(self, person_id: str) -> Person:
        pass


def test_openapi():
    app = Starlite(route_handlers=[PersonController])
    openapi_doc = create_openapi_schema(app=app)
    assert openapi_doc
