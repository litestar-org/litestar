"""Serialization, DTO and signature-model benchmarks (no network, no event loop unless noted)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

import pytest
from pytest_codspeed import BenchmarkFixture

from litestar import Litestar, get, post
from litestar.dto import DataclassDTO, DTOConfig
from litestar.dto._backend import DTOBackend
from litestar.dto._codegen_backend import DTOCodegenBackend
from litestar.params import FromQuery, JSONBody
from litestar.serialization import decode_json, encode_json
from litestar.testing import RequestFactory
from litestar.typing import FieldDefinition
from tests.benchmarks.helpers import ASGIRunner, make_scope, response_status

pytestmark = pytest.mark.benchmark

NAMESPACE = UUID("12345678-1234-5678-1234-567812345678")
CREATED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@dataclass
class Address:
    street: str
    city: str
    zip_code: str


@dataclass
class Person:
    id: UUID
    name: str
    email: str
    created_at: datetime
    address: Address
    tags: list[str]
    score: float


def make_people(count: int) -> list[Person]:
    return [
        Person(
            id=uuid5(NAMESPACE, str(i)),
            name=f"Person {i}",
            email=f"person{i}@example.com",
            created_at=CREATED_AT,
            address=Address(street=f"{i} Main St", city="Springfield", zip_code=f"{10000 + i}"),
            tags=["alpha", "beta", "gamma"],
            score=i * 1.5,
        )
        for i in range(count)
    ]


BACKENDS = pytest.mark.parametrize(
    "backend_cls", [DTOBackend, DTOCodegenBackend], ids=["default_backend", "codegen_backend"]
)


def test_encode_json_nested(benchmark: BenchmarkFixture) -> None:
    payload: dict[str, Any] = {
        "people": make_people(20),
        "generated_at": CREATED_AT,
        "request_id": uuid5(NAMESPACE, "request"),
        "meta": {"page": 1, "size": 20, "filters": ["active", "verified"]},
    }

    def encode_20_times() -> bytes:
        for _ in range(19):
            encode_json(payload)
        return encode_json(payload)

    encoded = benchmark(encode_20_times)
    assert encoded.startswith(b'{"people":[{"id":"')


def test_decode_json_typed(benchmark: BenchmarkFixture) -> None:
    raw = encode_json(make_people(20))

    def decode_10_times() -> list[Person]:
        for _ in range(9):
            decode_json(raw, target_type=list[Person])
        return decode_json(raw, target_type=list[Person])

    people = benchmark(decode_10_times)
    assert len(people) == 20
    assert isinstance(people[0].address, Address)


@BACKENDS
def test_dto_encode_list_100(
    benchmark: BenchmarkFixture, backend_cls: type[DTOBackend], reset_dto_backends: None
) -> None:
    class PersonDTO(DataclassDTO[Person]):
        pass

    PersonDTO.create_for_field_definition(
        FieldDefinition.from_annotation(list[Person]), handler_id="bench", backend_cls=backend_cls
    )
    backend = PersonDTO._dto_backends["bench"].get("return_backend")
    assert backend is not None
    people = make_people(100)
    encoded = benchmark(backend.encode_data, people)
    assert len(encoded) == 100


@BACKENDS
def test_dto_request_roundtrip(
    benchmark: BenchmarkFixture, backend_cls: type[DTOBackend], reset_dto_backends: None, runner: ASGIRunner
) -> None:
    class PersonDTO(DataclassDTO[Person]):
        config = DTOConfig(experimental_codegen_backend=backend_cls is DTOCodegenBackend)

    @post("/people", dto=PersonDTO, return_dto=PersonDTO)
    async def handler(data: JSONBody[Person]) -> Person:
        return data

    app = Litestar(route_handlers=[handler], openapi_config=None)
    body = encode_json(make_people(1)[0])
    scope = make_scope(
        "/people",
        method="POST",
        headers=[(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    )
    messages = benchmark(runner.request, app, scope, body)
    assert response_status(messages) == 201


def test_signature_model_parse(benchmark: BenchmarkFixture) -> None:
    @get("/search")
    async def handler(
        page: FromQuery[int],
        size: FromQuery[int],
        q: FromQuery[str],
        active: FromQuery[bool],
        ids: FromQuery[list[int]],
    ) -> None:
        return None

    app = Litestar(route_handlers=[handler], openapi_config=None)
    # routes[0] is the HTTPRoute for /search; route_handlers[0] is our GET handler, [1] the auto OPTIONS handler.
    route_handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    model = route_handler.signature_model
    connection = RequestFactory(app=app).get("/search")
    kwargs = {"page": "2", "size": "50", "q": "hello", "active": "true", "ids": ["1", "2", "3"]}

    def parse_100_times() -> Any:
        for _ in range(99):
            model.parse_values_from_connection_kwargs(connection, kwargs)
        return model.parse_values_from_connection_kwargs(connection, kwargs)

    parsed = benchmark(parse_100_times)
    assert parsed == {"page": 2, "size": 50, "q": "hello", "active": True, "ids": [1, 2, 3]}
