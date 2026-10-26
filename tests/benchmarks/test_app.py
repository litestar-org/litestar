"""Application startup, routing and OpenAPI generation benchmarks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from litestar import Litestar
from litestar._openapi.plugin import OpenAPIPlugin
from tests.benchmarks.apps import create_large_app

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture


@pytest.fixture(scope="module")
def large_app() -> Litestar:
    return create_large_app()


def test_app_creation_small(benchmark: BenchmarkFixture) -> None:
    app = benchmark(create_large_app, 1)
    assert app.route_handler_method_map


def test_app_creation_large(benchmark: BenchmarkFixture) -> None:
    app = benchmark(create_large_app, 20)
    assert app.route_handler_method_map


def test_openapi_schema_generation(benchmark: BenchmarkFixture, large_app: Litestar) -> None:
    plugin = large_app.plugins.get(OpenAPIPlugin)

    @benchmark
    def schema() -> dict[str, object]:
        plugin.invalidate_schema_cache()
        return plugin.provide_openapi_schema()

    assert schema["paths"]


@pytest.mark.parametrize(
    ("path", "method"),
    [
        pytest.param("/api/v0/resource0", "GET", id="static"),
        pytest.param("/api/v1/resource19/12345", "PUT", id="path_param"),
        pytest.param("/api/v2/resource17/42/items", "PATCH", id="nested_path_param"),
    ],
)
def test_route_resolution(benchmark: BenchmarkFixture, large_app: Litestar, path: str, method: str) -> None:
    # bypass the LRU cache to measure the actual trie traversal
    handle_routing = large_app.asgi_router._handle_routing

    @benchmark
    def result() -> object:
        return handle_routing(path=path, method=method)  # type: ignore[arg-type]

    assert result
