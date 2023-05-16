from __future__ import annotations

from dataclasses import dataclass

from litestar import Litestar, get


@dataclass
class Person:
    name: str
    age: int
    email: str


@get("/person/{name:str}", sync_to_thread=False)
def get_person(name: str) -> Person:
    # Your logic to retrieve the person goes here
    # For demonstration purposes, a placeholder Person instance is returned
    return Person(name=name, age=30, email=f"email_of_{name}@example.com")


app = Litestar(route_handlers=[get_person])
