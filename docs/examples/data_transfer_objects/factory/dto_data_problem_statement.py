from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig


@dataclass
class Person:
    id: UUID
    name: str
    age: int


class WriteDTO(DataclassDTO[Person]):
    """Do not allow client to set the id."""

    config = DTOConfig(exclude={"id"})


# We need a dto for the handler to parse the request data per the configuration, however,
# we do not need a return DTO as we are returning a dataclass, and Litestar already knows
# how to serialize dataclasses.
@post("/person", dto=WriteDTO, return_dto=None, sync_to_thread=False)
def create_person(data: Person) -> Person:
    """Create a person."""
    return data


app = Litestar(route_handlers=[create_person])

# run: /person -H "Content-Type: application/json" -d '{"name":"Peter","age":41}'
