"""Application startup, OpenAPI generation and routing-trie benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from pytest_codspeed import BenchmarkFixture

from litestar import Litestar, get
from litestar._openapi.plugin import OpenAPIPlugin
from litestar._signature import SignatureModel
from litestar.dto import DataclassDTO
from litestar.dto._backend import DTOBackend
from litestar.dto._codegen_backend import DTOCodegenBackend
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.config import OpenAPIConfig
from litestar.params import FromPath, FromQuery
from litestar.typing import FieldDefinition
from litestar.utils.signature import ParsedSignature

pytestmark = pytest.mark.benchmark


def make_handlers(count: int) -> list[HTTPRouteHandler]:
    handlers: list[HTTPRouteHandler] = []
    for index in range(count):

        @get(f"/resource{index}/{{item_id:int}}", name=f"resource_{index}")
        async def handler(item_id: FromPath[int], page: FromQuery[int] = 1) -> dict[str, int]:
            return {"item_id": item_id, "page": page}

        handlers.append(handler)
    return handlers


def openapi_config() -> OpenAPIConfig:
    return OpenAPIConfig(title="bench", version="1.0.0")


@pytest.mark.benchmark(max_rounds=10)  # walltime-only knob (local runs); simulation mode runs each benchmark once
@pytest.mark.parametrize("route_count", [10, 500], ids=["10_routes", "500_routes"])
def test_app_init(benchmark: BenchmarkFixture, route_count: int) -> None:
    handlers = make_handlers(route_count)
    app = benchmark(lambda: Litestar(route_handlers=handlers, openapi_config=openapi_config()))
    assert len(app.routes) >= route_count


@pytest.mark.benchmark(max_rounds=10)  # walltime-only knob (local runs); simulation mode runs each benchmark once
def test_openapi_schema_500_routes(benchmark: BenchmarkFixture) -> None:
    app = Litestar(route_handlers=make_handlers(500), openapi_config=openapi_config())
    plugin = app.plugins.get(OpenAPIPlugin)

    def build() -> dict[str, Any]:
        plugin.invalidate_schema_cache()
        return plugin.provide_openapi_schema()

    schema = benchmark(build)
    assert len(schema["paths"]) == 500


def test_signature_model_create(benchmark: BenchmarkFixture) -> None:
    async def fn(
        a: FromQuery[int],
        b: FromQuery[str],
        c: FromQuery[float],
        d: FromQuery[bool],
        e: FromQuery[list[int]],
        f: FromQuery[int | None] = None,
        g: FromQuery[str] = "default",
        h: FromQuery[list[str] | None] = None,
    ) -> None:
        return None

    parsed_signature = ParsedSignature.from_fn(fn, {})
    # Wrapped in a lambda rather than passed as `benchmark(SignatureModel.create, fn=fn, ...)`:
    # pytest-codspeed's instrumented measure() has its own positional parameter named `fn`, which
    # collides with SignatureModel.create's `fn` keyword under --codspeed (TypeError: multiple
    # values for argument 'fn').
    model = benchmark(
        lambda: SignatureModel.create(
            dependency_name_set=set(),
            fn=fn,
            parsed_signature=parsed_signature,
            data_dto=None,
            type_decoders=[],
        )
    )
    assert issubclass(model, SignatureModel)


@dataclass
class Address:
    street: str
    city: str


@dataclass
class Person:
    name: str
    email: str
    age: int
    address: Address
    tags: list[str]


@pytest.mark.parametrize("backend_cls", [DTOBackend, DTOCodegenBackend], ids=["default_backend", "codegen_backend"])
def test_dto_backend_create(
    benchmark: BenchmarkFixture, backend_cls: type[DTOBackend], reset_dto_backends: None
) -> None:
    class PersonDTO(DataclassDTO[Person]):
        pass

    field_definition = FieldDefinition.from_annotation(list[Person])

    def create() -> None:
        PersonDTO._dto_backends.clear()
        DTOBackend._seen_model_names = set()
        PersonDTO.create_for_field_definition(field_definition, handler_id="bench", backend_cls=backend_cls)

    benchmark(create)
    backend = PersonDTO._dto_backends["bench"].get("return_backend")
    assert backend is not None
    assert isinstance(backend, backend_cls)


def test_routing_trie_lookup_500(benchmark: BenchmarkFixture) -> None:
    """Measures the uncached trie traversal (``_handle_routing``); production requests
    normally hit the per-instance ``lru_cache`` in front of it.
    """
    app = Litestar(route_handlers=make_handlers(500), openapi_config=None)
    router = app.asgi_router
    paths = ["/resource0/1", "/resource250/42", "/resource499/7"]

    def lookup() -> list[dict[str, Any]]:
        # _handle_routing is the uncached implementation behind the lru_cache'd handle_routing.
        for _ in range(99):
            [router._handle_routing(path=path, method="GET")[3] for path in paths]
        return [router._handle_routing(path=path, method="GET")[3] for path in paths]

    params = benchmark(lookup)
    assert params == [{"item_id": 1}, {"item_id": 42}, {"item_id": 7}]
