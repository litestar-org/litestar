from __future__ import annotations

from dataclasses import dataclass

from litestar import Litestar, get
from litestar.dto import DataclassDTO, DTOConfig


@dataclass
class Address:
    street: str
    city: str
    country: str


@dataclass
class Person:
    name: str
    age: int
    email: str
    address: Address


class ReadDTO(DataclassDTO[Person]):
    config = DTOConfig(exclude={"email", "address.street"})


@get("/person/{name:str}", return_dto=ReadDTO, sync_to_thread=False)
def get_person(name: str) -> Person:
    # Your logic to retrieve the person goes here
    # For demonstration purposes, a placeholder Person instance is returned
    address = Address(street="123 Main St", city="Cityville", country="Countryland")
    return Person(
        name=name, age=30, email=f"email_of_{name}@example.com", address=address
    )


app = Litestar(route_handlers=[get_person])
