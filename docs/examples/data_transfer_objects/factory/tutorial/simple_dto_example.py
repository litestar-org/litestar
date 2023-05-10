from __future__ import annotations

from dataclasses import dataclass

from typing_extensions import Annotated

from litestar import Litestar, get, post
from litestar.dto.factory import DTOConfig
from litestar.dto.factory.stdlib.dataclass import DataclassDTO


@dataclass
class Person:
    name: str
    age: int
    email: str


config = DTOConfig(exclude={"email"})
ReadDTO = DataclassDTO[Annotated[Person, config]]


@post("/create-person")
def create_person(data: Person) -> Person:
    return data


@get("/person/{name:str}", dto=ReadDTO)
def get_person(name: str) -> Person:
    # Your logic to retrieve the person goes here
    # For demonstration purposes, a placeholder Person instance is returned
    return Person(name="John Doe", age=30, email="johndoe@example.com")


app = Litestar(route_handlers=[create_person, get_person])
