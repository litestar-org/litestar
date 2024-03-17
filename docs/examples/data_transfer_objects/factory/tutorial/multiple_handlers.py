from __future__ import annotations

from dataclasses import dataclass

from litestar import Litestar, patch, post, put
from litestar.dto import DataclassDTO, DTOConfig, DTOData


@dataclass
class Person:
    name: str
    age: int
    email: str
    id: int


class ReadDTO(DataclassDTO[Person]):
    config = DTOConfig(exclude={"email"})


class WriteDTO(DataclassDTO[Person]):
    config = DTOConfig(exclude={"id"})


class PatchDTO(DataclassDTO[Person]):
    config = DTOConfig(exclude={"id"}, partial=True)


@post("/person", dto=WriteDTO, return_dto=ReadDTO, sync_to_thread=False)
def create_person(data: DTOData[Person]) -> Person:
    # Logic for persisting the person goes here
    return data.create_instance(id=1)


@put("/person/{person_id:int}", dto=WriteDTO, return_dto=ReadDTO, sync_to_thread=False)
def update_person(person_id: int, data: DTOData[Person]) -> Person:
    # Usually the Person would be retrieved from a database
    person = Person(
        id=person_id, name="John", age=50, email="email_of_john@example.com"
    )
    return data.update_instance(person)


@patch(
    "/person/{person_id:int}", dto=PatchDTO, return_dto=ReadDTO, sync_to_thread=False
)
def patch_person(person_id: int, data: DTOData[Person]) -> Person:
    # Usually the Person would be retrieved from a database
    person = Person(
        id=person_id, name="John", age=50, email="email_of_john@example.com"
    )
    return data.update_instance(person)


app = Litestar(route_handlers=[create_person, update_person, patch_person])
