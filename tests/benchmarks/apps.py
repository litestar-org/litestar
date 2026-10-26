"""Shared applications and models used by the benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

import msgspec

from litestar import Controller, Litestar, MediaType, Router, delete, get, patch, post, put
from litestar.di import NamedDependency, Provide
from litestar.dto import DataclassDTO, DTOConfig
from litestar.params import FromPath, FromQuery, HeaderParameter, JSONBody


class Address(msgspec.Struct):
    street: str
    city: str
    country: str
    zip_code: str


class Person(msgspec.Struct):
    id: int
    first_name: str
    last_name: str
    email: str
    age: int
    tags: list[str]
    address: Address
    created_at: datetime


@dataclass
class Item:
    name: str
    price: float
    quantity: int
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    id: UUID | None = None


class ItemWriteDTO(DataclassDTO[Item]):
    config = DTOConfig(exclude={"id"})


class ItemReadDTO(DataclassDTO[Item]): ...


def make_person(i: int) -> Person:
    return Person(
        id=i,
        first_name=f"First{i}",
        last_name=f"Last{i}",
        email=f"person{i}@example.com",
        age=20 + i % 50,
        tags=["alpha", "beta", "gamma"],
        address=Address(street=f"{i} Main Street", city="Springfield", country="US", zip_code="12345"),
        created_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )


PEOPLE = [make_person(i) for i in range(100)]
PERSON_JSON = msgspec.json.encode(make_person(1))
ITEM_JSON = msgspec.json.encode(
    {"name": "Widget", "price": 9.99, "quantity": 3, "description": "A widget", "tags": ["a", "b", "c"]}
)


@get("/plaintext", media_type=MediaType.TEXT, sync_to_thread=False)
def plaintext() -> str:
    return "Hello, World!"


@get("/plaintext-async", media_type=MediaType.TEXT)
async def plaintext_async() -> str:
    return "Hello, World!"


@get("/json", sync_to_thread=False)
def json_dict() -> dict[str, Any]:
    return {"message": "Hello, World!", "count": 42, "items": [1, 2, 3]}


@get("/people", sync_to_thread=False)
def people() -> list[Person]:
    return PEOPLE


@get("/users/{user_id:int}/posts/{post_id:str}", sync_to_thread=False)
def path_params(user_id: FromPath[int], post_id: FromPath[str]) -> dict[str, Any]:
    return {"user_id": user_id, "post_id": post_id}


@get("/search", sync_to_thread=False)
def query_params(
    q: FromQuery[str],
    page: FromQuery[int] = 1,
    page_size: FromQuery[int] = 20,
    tags: FromQuery[list[str] | None] = None,
    x_request_id: Annotated[str | None, HeaderParameter(name="x-request-id")] = None,
) -> dict[str, Any]:
    return {"q": q, "page": page, "page_size": page_size, "tags": tags, "request_id": x_request_id}


@post("/person", sync_to_thread=False)
def create_person(data: JSONBody[Person]) -> Person:
    return data


@post("/raw", sync_to_thread=False)
def create_raw(data: JSONBody[dict[str, Any]]) -> dict[str, Any]:
    return data


@post("/items", dto=ItemWriteDTO, return_dto=ItemReadDTO, sync_to_thread=False)
def create_item(data: JSONBody[Item]) -> Item:
    data.id = UUID("12345678-1234-5678-1234-567812345678")
    return data


async def provide_settings() -> dict[str, str]:
    return {"env": "bench"}


def provide_db(settings: NamedDependency[dict[str, str]]) -> dict[str, Any]:
    return {"settings": settings, "connected": True}


def provide_repository(db: NamedDependency[dict[str, Any]]) -> dict[str, Any]:
    return {"db": db}


@get(
    "/dependencies",
    dependencies={
        "settings": Provide(provide_settings),
        "db": Provide(provide_db, sync_to_thread=False),
        "repository": Provide(provide_repository, sync_to_thread=False),
    },
    sync_to_thread=False,
)
def with_dependencies(repository: NamedDependency[dict[str, Any]]) -> dict[str, Any]:
    return {"ok": repository["db"]["connected"]}


def create_request_app() -> Litestar:
    return Litestar(
        route_handlers=[
            plaintext,
            plaintext_async,
            json_dict,
            people,
            path_params,
            query_params,
            create_person,
            create_raw,
            create_item,
            with_dependencies,
        ],
        openapi_config=None,
    )


def create_large_app(num_controllers: int = 20) -> Litestar:
    """Create an application with many controllers and routes, mimicking a mid-sized real-world API."""
    routers = []
    for i in range(num_controllers):

        class ResourceController(Controller):
            path = f"/resource{i}"
            tags = [f"resource{i}"]

            @get("/", sync_to_thread=False)
            def list_items(self, limit: FromQuery[int] = 10, offset: FromQuery[int] = 0) -> list[Person]:
                return PEOPLE[offset : offset + limit]

            @get("/{item_id:int}", sync_to_thread=False)
            def get_item(self, item_id: FromPath[int]) -> Person:
                return PEOPLE[item_id]

            @post("/", sync_to_thread=False)
            def create_item(self, data: JSONBody[Person]) -> Person:
                return data

            @put("/{item_id:int}", sync_to_thread=False)
            def update_item(self, item_id: FromPath[int], data: JSONBody[Person]) -> Person:
                return data

            @patch("/{item_id:int}/items", dto=ItemWriteDTO, return_dto=ItemReadDTO, sync_to_thread=False)
            def patch_item(self, item_id: FromPath[int], data: JSONBody[Item]) -> Item:
                return data

            @delete("/{item_id:int}", sync_to_thread=False)
            def delete_item(self, item_id: FromPath[int]) -> None:
                return None

        ResourceController.__name__ = f"ResourceController{i}"
        routers.append(Router(path=f"/api/v{i % 3}", route_handlers=[ResourceController]))

    return Litestar(route_handlers=routers)
