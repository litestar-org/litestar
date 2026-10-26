"""End-to-end request handling benchmarks, driving the ASGI application in-process."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from litestar import Litestar
from tests.benchmarks.apps import ITEM_JSON, PERSON_JSON, create_request_app

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

    from tests.benchmarks.conftest import ASGIDriver


@pytest.fixture()
def app() -> Litestar:
    return create_request_app()


JSON_HEADERS = [(b"content-type", b"application/json")]


def test_plaintext(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/plaintext")

    assert result == (200, b"Hello, World!")


def test_plaintext_async_handler(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/plaintext-async")

    assert result == (200, b"Hello, World!")


def test_json_response(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/json")

    assert result[0] == 200


def test_json_response_list_of_structs(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/people")

    assert result[0] == 200


def test_path_params(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/users/42/posts/hello-world")

    assert result == (200, b'{"user_id":42,"post_id":"hello-world"}')


def test_query_and_header_params(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    headers = [(b"x-request-id", b"abc-123")]

    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(
            app, path="/search", query_string=b"q=litestar&page=2&page_size=50&tags=a&tags=b", headers=headers
        )

    assert result[0] == 200


def test_json_body_struct(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, method="POST", path="/person", headers=JSON_HEADERS, body=PERSON_JSON)

    assert result[0] == 201


def test_json_body_dict(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, method="POST", path="/raw", headers=JSON_HEADERS, body=PERSON_JSON)

    assert result[0] == 201


def test_dto_round_trip(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, method="POST", path="/items", headers=JSON_HEADERS, body=ITEM_JSON)

    assert result[0] == 201


def test_dependency_injection(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/dependencies")

    assert result == (200, b'{"ok":true}')


def test_not_found(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/does-not-exist")

    assert result[0] == 404


def test_validation_error(benchmark: BenchmarkFixture, app: Litestar, asgi_driver: ASGIDriver) -> None:
    @benchmark
    def result() -> tuple[int, bytes]:
        return asgi_driver.request(app, path="/search", query_string=b"page=not-a-number")

    assert result[0] == 400
