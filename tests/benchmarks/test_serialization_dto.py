"""Serialization, DTO and request parameter validation benchmarks.

Only ``test_dto_request_roundtrip`` goes through the ASGI interface; it starts the app and
sends 10 requests per measured call like the request-path benchmarks. The rest call the
libraries directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

import pytest
from pytest_codspeed import BenchmarkFixture

from litestar import Litestar, get, post
from litestar._request_parameters.validation import RequestParameterValidator
from litestar.dto import DataclassDTO, DTOConfig
from litestar.dto._backend import DTOBackend
from litestar.dto._codegen_backend import DTOCodegenBackend
from litestar.params import FromQuery, JSONBody
from litestar.serialization import decode_json, encode_json
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
    with runner.lifespan(app):
        messages = benchmark(runner.request_many, app, scope, body)
    assert response_status(messages) == 201


def test_request_parameter_validation(benchmark: BenchmarkFixture) -> None:
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
    route_handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    definitions = route_handler._injection_setup.request_parameter_definitions.values()
    validator = RequestParameterValidator(definitions, type_decoders=route_handler.type_decoders)
    values = {"page": "2", "size": "50", "q": "hello", "active": "true", "ids": ["1", "2", "3"]}
    raw = {definition.key: values[definition.name] for definition in definitions}

    def validate_100_times() -> dict[str, Any]:
        for _ in range(99):
            validator.validate(raw)
        return validator.validate(raw)

    validated = benchmark(validate_100_times)
    assert {definition.name: validated[definition.key] for definition in definitions} == {
        "page": 2,
        "size": 50,
        "q": "hello",
        "active": True,
        "ids": [1, 2, 3],
    }
