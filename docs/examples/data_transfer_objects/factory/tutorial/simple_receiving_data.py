from __future__ import annotations

from dataclasses import dataclass

from litestar import Litestar, post
from litestar.dto import DataclassDTO, DTOConfig
from litestar.params import JSONBody


@dataclass
class Person:
    name: str
    age: int
    email: str


class ReadDTO(DataclassDTO[Person]):
    config = DTOConfig(exclude={"email"})


@post("/person", return_dto=ReadDTO, sync_to_thread=False)
def create_person(data: JSONBody[Person]) -> Person:
    # Logic for persisting the person goes here
    return data


app = Litestar(route_handlers=[create_person])
