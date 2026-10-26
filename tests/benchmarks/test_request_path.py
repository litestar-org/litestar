"""Per-request hot path benchmarks, mirroring the scenarios in docs/benchmarks.rst."""

from __future__ import annotations

import pytest
from pytest_codspeed import BenchmarkFixture

from litestar import Litestar, MediaType, get
from tests.benchmarks.helpers import ASGIRunner, make_scope, response_body, response_status

pytestmark = pytest.mark.benchmark


@get("/plaintext", media_type=MediaType.TEXT)
async def plaintext() -> str:
    return "Hello, world!"


@pytest.fixture(scope="module")
def app() -> Litestar:
    return Litestar(route_handlers=[plaintext], openapi_config=None)


def test_plaintext_get(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/plaintext")
    messages = benchmark(runner.request, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b"Hello, world!"
