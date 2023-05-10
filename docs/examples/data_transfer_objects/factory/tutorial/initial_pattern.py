from __future__ import annotations

from dataclasses import dataclass

from litestar import Litestar, post


@dataclass
class Person:
    name: str
    age: int
    email: str


@post("/create-person")
def create_person(data: Person) -> Person:
    return data


app = Litestar(route_handlers=[create_person])
