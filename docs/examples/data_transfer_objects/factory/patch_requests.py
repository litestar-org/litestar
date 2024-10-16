from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar import Litestar, patch
from litestar.dto import DataclassDTO, DTOConfig, DTOData


@dataclass
class Person:
    id: UUID
    name: str
    age: int


class PatchDTO(DataclassDTO[Person]):
    """Don't allow client to set the id, and allow partial updates."""

    config = DTOConfig(exclude={"id"}, partial=True)


peter_uuid = UUID("f32ff2ce-e32f-4537-9dc0-26e7599f1380")
database = {
    peter_uuid: Person(id=peter_uuid, name="Peter", age=40)
}


@patch("/person/{person_id:uuid}", dto=PatchDTO, return_dto=None, sync_to_thread=False)
def update_person(person_id: UUID, data: DTOData[Person]) -> Person:
    """Partially update a person."""
    return data.update_instance(database[person_id])


app = Litestar(route_handlers=[update_person])

# run: /person/f32ff2ce-e32f-4537-9dc0-26e7599f1380 -X PATCH -H "Content-Type: application/json" -d '{"name":"Peter Pan"}'
