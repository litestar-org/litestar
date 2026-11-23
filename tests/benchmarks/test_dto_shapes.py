from dataclasses import dataclass, field
from typing import Annotated, Any

import pytest
from pytest_codspeed import BenchmarkFixture

from litestar import Litestar, post
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig
from litestar.dto._backend import DTOBackend
from litestar.params import JSONBody
from litestar.serialization import encode_json
from litestar.typing import FieldDefinition
from tests.benchmarks.helpers import ASGIRunner, make_scope, response_body, response_status

pytestmark = pytest.mark.benchmark


@dataclass
class Product:
    sku: str
    name: str
    price: float
    internal_cost: float = 0.0


@dataclass
class LineItem:
    product: Product
    quantity: int
    note: str = ""


@dataclass
class Address:
    street: str
    city: str
    zip_code: str


@dataclass
class Customer:
    name: str
    email: str
    address: Address


@dataclass
class Order:
    reference: str
    customer: Customer
    items: list[LineItem]
    tags: list[str] = field(default_factory=list)


@dataclass
class Shipment:
    reference: str
    destination: Address | None
    contact: Address | str
    weight: int | float | None
    stops: list[Address | str]
    notes: str | None = None


@dataclass
class Node:
    name: str
    children: "list[Node]" = field(default_factory=list)
    parent: "Node | None" = None


_json_body: Any = JSONBody


def make_order() -> Order:
    return Order(
        reference="order-1",
        customer=Customer(
            name="Person 1",
            email="person1@example.com",
            address=Address(street="1 Main St", city="Springfield", zip_code="10001"),
        ),
        items=[
            LineItem(
                product=Product(sku=f"sku-{i}", name=f"Product {i}", price=i * 1.5, internal_cost=i * 1.0),
                quantity=i,
                note="fragile",
            )
            for i in range(20)
        ],
        tags=["alpha", "beta", "gamma"],
    )


def make_shipment() -> Shipment:
    address = Address(street="1 Main St", city="Springfield", zip_code="10001")
    return Shipment(
        reference="shipment-1",
        destination=address,
        contact="dock 4",
        weight=12.5,
        stops=[address if i % 2 else f"stop {i}" for i in range(20)],
    )


def roundtrip(
    benchmark: BenchmarkFixture, runner: ASGIRunner, dto: type[AbstractDTO[Any]], annotation: Any, payload: Any
) -> bytes:
    async def handler(data: Any) -> Any:
        return data

    handler.__annotations__.update({"data": _json_body[annotation], "return": annotation})
    app = Litestar(route_handlers=[post("/items", dto=dto, return_dto=dto)(handler)], openapi_config=None)
    body = encode_json(payload)
    scope = make_scope(
        "/items",
        method="POST",
        headers=[(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    )
    with runner.lifespan(app):
        messages = benchmark(runner.request_many, app, scope, body)
    assert response_status(messages) == 201
    return response_body(messages)


def test_dto_nested_roundtrip(benchmark: BenchmarkFixture, reset_dto_backends: None, runner: ASGIRunner) -> None:
    config = DTOConfig(
        max_nested_depth=2,
        exclude={"items.0.product.internal_cost"},
    )
    body = roundtrip(benchmark, runner, DataclassDTO[Annotated[Order, config]], Order, make_order())
    assert body.count(b'"sku"') == 20
    assert b"internal_cost" not in body


def test_dto_union_roundtrip(benchmark: BenchmarkFixture, reset_dto_backends: None, runner: ASGIRunner) -> None:
    config = DTOConfig(exclude={"notes"})
    body = roundtrip(benchmark, runner, DataclassDTO[Annotated[Shipment, config]], Shipment, make_shipment())
    assert body.count(b'"street"') == 11
    assert b"notes" not in body


def test_dto_pydantic_roundtrip(benchmark: BenchmarkFixture, reset_dto_backends: None, runner: ASGIRunner) -> None:
    pydantic = pytest.importorskip("pydantic")
    from litestar.plugins.pydantic import PydanticDTO

    address_model = pydantic.create_model("PydanticAddress", street=(str, ...), city=(str, ...), zip_code=(str, ...))
    person_model = pydantic.create_model(
        "PydanticPerson",
        name=(str, ...),
        email=(str, ...),
        age=(int, pydantic.Field(ge=0)),
        address=(address_model, ...),
        tags=(list[str], ...),
        internal_note=(str, ""),
    )
    config = DTOConfig(exclude={"internal_note"})
    payload = {
        "name": "Person 1",
        "email": "person1@example.com",
        "age": 30,
        "address": {"street": "1 Main St", "city": "Springfield", "zip_code": "10001"},
        "tags": ["alpha", "beta", "gamma"],
    }
    pydantic_dto: Any = PydanticDTO
    body = roundtrip(benchmark, runner, pydantic_dto[Annotated[person_model, config]], person_model, payload)
    assert b'"city":"Springfield"' in body
    assert b"internal_note" not in body


@pytest.mark.parametrize("depth", [2, 4, 8])
def test_dto_backend_create_self_referential(benchmark: BenchmarkFixture, depth: int, reset_dto_backends: None) -> None:
    class NodeDTO(DataclassDTO[Node]):
        config = DTOConfig(max_nested_depth=depth)

    field_definition = FieldDefinition.from_annotation(Node)

    def create() -> None:
        NodeDTO._dto_backends.pop("self_referential", None)
        DTOBackend._seen_model_names = set()
        NodeDTO.create_for_field_definition(field_definition, handler_id="self_referential")

    benchmark(create)
    backend = NodeDTO._dto_backends.pop("self_referential").get("return_backend")
    assert backend is not None
    assert len(backend.parsed_field_definitions) == 3
