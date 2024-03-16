from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig, DTOData


@dataclass
class Person:
    id: UUID
    name: str
    age: int


class WriteDTO(DataclassDTO[Person]):
    """Do not allow client to set the id."""

    config = DTOConfig(exclude={"id"})


@post("/person", dto=WriteDTO, return_dto=None, sync_to_thread=False)
def create_person(data: DTOData[Person]) -> Person:
    """Create a person."""
    return data.create_instance(id=uuid4())


app = Litestar(route_handlers=[create_person])

# run: /person -H "Content-Type: application/json" -d '{"name":"Peter","age":41}'
