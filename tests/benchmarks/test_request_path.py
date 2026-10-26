"""Per-request hot path benchmarks, mirroring the scenarios in docs/benchmarks.rst.

Each benchmark sends 10 requests per measured call; see ``ASGIRunner.request_many``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated, Any

import msgspec
import pytest
from pytest_codspeed import BenchmarkFixture

from litestar import Litestar, MediaType, get, post
from litestar.config.cors import CORSConfig
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotFoundException
from litestar.middleware import ASGIMiddleware
from litestar.params import CookieParameter, FromPath, FromQuery, HeaderParameter, JSONBody
from litestar.types import ASGIApp, Receive, Scope, Send
from tests.benchmarks.helpers import ASGIRunner, make_scope, response_body, response_status

pytestmark = pytest.mark.benchmark


@dataclass
class Item:
    name: str
    price: float
    tags: list[str]


class ItemStruct(msgspec.Struct):
    name: str
    price: float
    tags: list[str]


ITEM_JSON = b'{"name":"widget","price":9.99,"tags":["alpha","beta","gamma"]}'
JSON_HEADERS = ((b"content-type", b"application/json"), (b"content-length", str(len(ITEM_JSON)).encode()))


@get("/plaintext", media_type=MediaType.TEXT)
async def plaintext() -> str:
    return "Hello, world!"


@get("/plaintext-sync", media_type=MediaType.TEXT, sync_to_thread=False)
def plaintext_sync() -> str:
    return "Hello, world!"


@get("/json")
async def json_dict() -> dict[str, Any]:
    return {"message": "Hello, world!", "count": 3, "items": ["alpha", "beta", "gamma"]}


ITEM_STRUCTS = [
    ItemStruct(name=f"item-{index}", price=index * 1.5, tags=["alpha", "beta", "gamma"]) for index in range(100)
]


@get("/items/structs")
async def json_struct_list() -> list[ItemStruct]:
    return ITEM_STRUCTS


@get("/items/{item_id:int}")
async def path_param(item_id: FromPath[int]) -> dict[str, int]:
    return {"item_id": item_id}


@get("/query")
async def query_params(page: FromQuery[int], tags: FromQuery[list[str]]) -> dict[str, Any]:
    return {"page": page, "tags": tags}


@get("/headers")
async def header_and_cookie(
    token: Annotated[str, HeaderParameter(name="x-token")],
    session_id: Annotated[str, CookieParameter(name="session_id")],
) -> dict[str, str]:
    return {"token": token, "session_id": session_id}


@post("/items/dataclass")
async def post_dataclass(data: JSONBody[Item]) -> Item:
    return data


@post("/items/struct")
async def post_struct(data: JSONBody[ItemStruct]) -> ItemStruct:
    return data


async def async_dep_a() -> int:
    return 1


async def async_dep_b(a: NamedDependency[int]) -> int:
    return a + 1


async def async_dep_c(b: NamedDependency[int]) -> int:
    return b + 1


def sync_dep_a() -> int:
    return 1


def sync_dep_b(a: NamedDependency[int]) -> int:
    return a + 1


def sync_dep_c(b: NamedDependency[int]) -> int:
    return b + 1


async def generator_dep() -> AsyncGenerator[int, None]:
    yield 1


@get(
    "/di/async",
    dependencies={"a": Provide(async_dep_a), "b": Provide(async_dep_b), "c": Provide(async_dep_c)},
)
async def di_async(c: NamedDependency[int]) -> dict[str, int]:
    return {"c": c}


@get(
    "/di/sync",
    dependencies={
        "a": Provide(sync_dep_a, sync_to_thread=False),
        "b": Provide(sync_dep_b, sync_to_thread=False),
        "c": Provide(sync_dep_c, sync_to_thread=False),
    },
)
async def di_sync(c: NamedDependency[int]) -> dict[str, int]:
    return {"c": c}


@get("/di/generator", dependencies={"value": Provide(generator_dep)})
async def di_generator(value: NamedDependency[int]) -> dict[str, int]:
    return {"value": value}


@get("/raise")
async def raise_not_found() -> None:
    raise NotFoundException("missing")


class NoopMiddleware(ASGIMiddleware):
    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        await next_app(scope, receive, send)


@pytest.fixture(scope="module")
def app() -> Litestar:
    return Litestar(
        route_handlers=[
            plaintext,
            plaintext_sync,
            json_dict,
            json_struct_list,
            path_param,
            query_params,
            header_and_cookie,
            post_dataclass,
            post_struct,
            di_async,
            di_sync,
            di_generator,
            raise_not_found,
        ],
        openapi_config=None,
    )


@pytest.fixture(scope="module")
def cors_app() -> Litestar:
    return Litestar(
        route_handlers=[json_dict],
        cors_config=CORSConfig(allow_origins=["https://example.com"]),
        openapi_config=None,
    )


@pytest.fixture(scope="module")
def middleware_app() -> Litestar:
    return Litestar(
        route_handlers=[json_dict],
        middleware=[NoopMiddleware(), NoopMiddleware(), NoopMiddleware()],
        openapi_config=None,
    )


def test_plaintext_get(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/plaintext")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b"Hello, world!"


def test_plaintext_get_sync_handler(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/plaintext-sync")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b"Hello, world!"


def test_json_dict_get(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/json")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert b'"count":3' in response_body(messages)


def test_json_struct_list_100_get(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/items/structs")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages).count(b'"name":"item-') == 100


def test_path_param_int(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/items/12345")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b'{"item_id":12345}'


def test_query_params_int_and_list(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/query", query_string=b"page=2&tags=alpha&tags=beta&tags=gamma")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b'{"page":2,"tags":["alpha","beta","gamma"]}'


def test_header_and_cookie_params(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/headers", headers=[(b"x-token", b"secret"), (b"cookie", b"session_id=abc123; theme=dark")])
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b'{"token":"secret","session_id":"abc123"}'


def test_post_json_dataclass(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/items/dataclass", method="POST", headers=JSON_HEADERS)
    messages = benchmark(runner.request_many, app, scope, ITEM_JSON)
    assert response_status(messages) == 201
    assert response_body(messages) == ITEM_JSON


def test_post_json_struct(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/items/struct", method="POST", headers=JSON_HEADERS)
    messages = benchmark(runner.request_many, app, scope, ITEM_JSON)
    assert response_status(messages) == 201
    assert response_body(messages) == ITEM_JSON


def test_di_nested_async_3(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/di/async")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b'{"c":3}'


def test_di_nested_sync_3(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/di/sync")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b'{"c":3}'


def test_di_generator_cleanup(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/di/generator")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 200
    assert response_body(messages) == b'{"value":1}'


def test_cors_simple_request(cors_app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/json", headers=[(b"origin", b"https://example.com")])
    messages = benchmark(runner.request_many, cors_app, scope)
    assert response_status(messages) == 200
    headers = dict(messages[0]["headers"])  # type: ignore[typeddict-item]
    assert headers[b"access-control-allow-origin"] == b"https://example.com"


def test_middleware_stack_3_asgi(middleware_app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/json")
    messages = benchmark(runner.request_many, middleware_app, scope)
    assert response_status(messages) == 200


def test_exception_http_raise(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/raise")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 404
    assert b'"detail":"missing"' in response_body(messages)


def test_exception_no_route(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/does/not/exist")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 404


def test_exception_query_validation(app: Litestar, runner: ASGIRunner, benchmark: BenchmarkFixture) -> None:
    scope = make_scope("/query", query_string=b"page=not-a-number&tags=alpha")
    messages = benchmark(runner.request_many, app, scope)
    assert response_status(messages) == 400
    assert b"page" in response_body(messages)
