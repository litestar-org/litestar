# pyright: reportUnnecessaryTypeIgnoreComment=false

import random
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Optional, TypeVar, Union
from unittest.mock import MagicMock
from uuid import uuid4

import msgspec
import pytest

from litestar import Litestar, Request, Response, get, post
from litestar.background_tasks import BackgroundTask
from litestar.config.compression import CompressionConfig
from litestar.config.csrf import CSRFConfig
from litestar.config.response_cache import CACHE_FOREVER, ResponseCacheConfig
from litestar.datastructures import Cookie, ResponseHeader, State
from litestar.di import NamedDependency, Provide
from litestar.dto import DataclassDTO, DTOConfig
from litestar.enums import CompressionEncoding
from litestar.middleware.session.base import BaseBackendConfig
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.params import FromPath
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.response import Redirect, Stream, Template
from litestar.response.base import ASGIResponse
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_301_MOVED_PERMANENTLY,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from litestar.stores.base import Store
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import TestClient, create_test_client
from litestar.types import HTTPScope

if TYPE_CHECKING:
    from time_machine import Traveller

T = TypeVar("T")


class _EnvelopeResponse(Response):
    def render(self, content: Any, media_type: str, enc_hook: Any = None) -> bytes:
        return super().render({"data": content}, media_type)

    def to_asgi_response(self, *args: Any, **kwargs: Any) -> ASGIResponse:
        asgi_response = super().to_asgi_response(*args, **kwargs)
        asgi_response.headers["x-envelope"] = "1"
        return asgi_response


class _RequestIdResponse(Response):
    def to_asgi_response(self, request: Request, **kwargs: Any) -> ASGIResponse:
        asgi_response = super().to_asgi_response(request, **kwargs)
        asgi_response.headers["x-request-id"] = request.headers.get("x-request-id", "")
        return asgi_response


@dataclass
class _User:
    name: str
    secret: str


@pytest.fixture()
def mock() -> MagicMock:
    return MagicMock(return_value=str(random.random()))


def after_request_handler(response: "Response[T]") -> "Response[T]":
    response.headers["unique-identifier"] = str(uuid4())
    return response


@pytest.mark.parametrize("sync_to_thread", (True, False))
def test_default_cache_response(sync_to_thread: bool, mock: MagicMock) -> None:
    @get(
        "/cached",
        sync_to_thread=sync_to_thread,
        cache=True,
        type_encoders={int: str},  # test pickling issues. see https://github.com/litestar-org/litestar/issues/1096
    )
    def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    with create_test_client([handler], after_request=after_request_handler) as client:
        first_response = client.get("/cached")
        second_response = client.get("/cached")

        first_response_identifier = first_response.headers["unique-identifier"]

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert second_response.headers["unique-identifier"] != first_response_identifier
        assert second_response.headers["content-type"] == first_response.headers["content-type"]
        assert first_response.text == second_response.text
        assert mock.call_count == 1


def test_handler_expiration(mock: MagicMock, frozen_datetime: "Traveller") -> None:
    @get("/cached-local", cache=10)
    async def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    with create_test_client([handler], after_request=after_request_handler) as client:
        first_response = client.get("/cached-local")
        frozen_datetime.shift(delta=timedelta(seconds=5))
        second_response = client.get("/cached-local")
        assert first_response.headers["unique-identifier"] != second_response.headers["unique-identifier"]
        assert mock.call_count == 1

        frozen_datetime.shift(delta=timedelta(seconds=11))
        third_response = client.get("/cached-local")
        assert first_response.headers["unique-identifier"] != third_response.headers["unique-identifier"]
        assert mock.call_count == 2


def test_default_expiration(mock: MagicMock, frozen_datetime: "Traveller") -> None:
    @get("/cached-default", cache=True)
    async def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    with create_test_client(
        [handler], after_request=after_request_handler, response_cache_config=ResponseCacheConfig(default_expiration=1)
    ) as client:
        first_response = client.get("/cached-default")
        second_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] != second_response.headers["unique-identifier"]
        assert mock.call_count == 1

        frozen_datetime.shift(delta=timedelta(seconds=1))
        third_response = client.get("/cached-default")
        assert first_response.headers["unique-identifier"] != third_response.headers["unique-identifier"]
        assert mock.call_count == 2


@pytest.mark.parametrize("expiration,expected_expiration", [(True, None), (10, 10)])
def test_default_expiration_none(
    memory_store: MemoryStore, expiration: int, expected_expiration: Optional[int]
) -> None:
    @get("/cached", cache=expiration)
    def handler() -> None:
        return None

    app = Litestar(
        [handler],
        stores={"response_cache": memory_store},
        response_cache_config=ResponseCacheConfig(default_expiration=None),
    )

    with TestClient(app) as client:
        client.get("/cached")

    if expected_expiration is None:
        assert memory_store._store["GET/cached"].expires_at is None
    else:
        assert memory_store._store["GET/cached"].expires_at


def test_cache_forever(memory_store: MemoryStore) -> None:
    @get("/cached", cache=CACHE_FOREVER)
    async def handler() -> None:
        return None

    app = Litestar([handler], stores={"response_cache": memory_store})

    with TestClient(app) as client:
        client.get("/cached")

    assert memory_store._store["GET/cached"].expires_at is None


@pytest.mark.parametrize("sync_to_thread", (True, False))
async def test_custom_cache_key(sync_to_thread: bool, anyio_backend: str, mock: MagicMock) -> None:
    def custom_cache_key_builder(request: Request[Any, Any, State]) -> str:
        return f"{request.url.path}:::cached"

    @get("/cached", sync_to_thread=sync_to_thread, cache=True, cache_key_builder=custom_cache_key_builder)
    def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    app = Litestar([handler])

    with TestClient(app) as client:
        client.get("/cached")
        store = app.stores.get("response_cache")
        assert await store.exists("/cached:::cached")


async def test_config_cache_key_builder(mock: MagicMock) -> None:
    def config_cache_key_builder(request: Request[Any, Any, State]) -> str:
        return f"{request.url.path}:::config"

    @get("/cached", cache=True)
    def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    app = Litestar([handler], response_cache_config=ResponseCacheConfig(key_builder=config_cache_key_builder))

    with TestClient(app) as client:
        assert client.get("/cached").text == mock.return_value
        assert client.get("/cached").text == mock.return_value

        assert mock.call_count == 1

    assert await app.stores.get("response_cache").exists("/cached:::config")


async def test_non_default_store_name(mock: MagicMock) -> None:
    @get(cache=True)
    def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    app = Litestar([handler], response_cache_config=ResponseCacheConfig(store="some_store"))

    with TestClient(app=app) as client:
        response_one = client.get("/")
        assert response_one.status_code == 200
        assert response_one.text == mock.return_value

        response_two = client.get("/")
        assert response_two.status_code == 200
        assert response_two.text == mock.return_value

        assert mock.call_count == 1

    assert await app.stores.get("some_store").exists("GET/")


async def test_with_stores(store: Store, mock: MagicMock) -> None:
    @get(cache=True)
    def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    app = Litestar([handler], stores={"response_cache": store})

    with TestClient(app=app) as client:
        response_one = client.get("/")
        assert response_one.status_code == 200
        assert response_one.text == mock.return_value

        response_two = client.get("/")
        assert response_two.status_code == 200
        assert response_two.text == mock.return_value

        assert mock.call_count == 1


def test_does_not_apply_to_non_cached_routes(mock: MagicMock) -> None:
    @get("/")
    def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    with create_test_client([handler]) as client:
        first_response = client.get("/")
        second_response = client.get("/")

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert mock.call_count == 2


async def test_does_not_cache_non_cached_handler_on_cached_route() -> None:
    @get("/mix", cache=True)
    async def cached() -> str:
        return "cached"

    @post("/mix")
    async def uncached() -> str:
        return "uncached"

    app = Litestar([cached, uncached])

    with TestClient(app) as client:
        client.get("/mix")
        client.post("/mix")

    store = app.stores.get("response_cache")
    assert await store.exists("GET/mix")
    assert not await store.exists("POST/mix")


@pytest.mark.parametrize(
    "cache,expect_applied",
    [
        (True, True),
        (False, False),
        (1, True),
        (CACHE_FOREVER, True),
    ],
)
async def test_cache_only_applied_to_cached_handlers(
    cache: Union[bool, int, type[CACHE_FOREVER]], expect_applied: bool
) -> None:
    @get(path="/", cache=cache)
    def handler() -> None: ...

    with create_test_client(route_handlers=[handler]) as client:
        client.get("/")
        assert await client.app.stores.get("response_cache").exists("GET/") is expect_applied


@pytest.mark.parametrize("session_config", [ServerSideSessionConfig(), CookieBackendConfig(secret=b"x" * 16)])
def test_cached_response_does_not_replay_set_cookie(session_config: BaseBackendConfig) -> None:
    @post("/login", sync_to_thread=False)
    def login(request: Request) -> None:
        request.set_session({"user": "admin"})

    @get("/public", cache=True, sync_to_thread=False)
    def public() -> str:
        return "public"

    app = Litestar([login, public], middleware=[session_config.middleware])

    with TestClient(app) as client:
        client.post("/login")
        victim_cookies = client.get("/public").headers.get_list("set-cookie")
        client.cookies.clear()
        other_cookies = client.get("/public").headers.get_list("set-cookie")

    assert victim_cookies
    assert not set(victim_cookies) & set(other_cookies)


def test_response_own_headers_are_cached_without_cookies(mock: MagicMock) -> None:
    def after(response: Response) -> Response:
        response.headers["x-after"] = str(uuid4())
        return response

    @get(
        "/",
        cache=True,
        sync_to_thread=False,
        after_request=after,
        response_cookies=[Cookie(key="layered", value="1")],
    )
    def handler() -> Response[str]:
        mock()
        return Response("x", headers={"x-handler": "1", "ETag": '"abc"'}, status_code=203)

    with create_test_client([handler]) as client:
        first = client.get("/")
        second = client.get("/")

    assert mock.call_count == 1
    assert second.status_code == first.status_code == 203
    assert second.text == "x"
    assert second.headers["x-handler"] == "1"
    assert second.headers["etag"] == '"abc"'
    assert first.headers["x-after"] != second.headers["x-after"]
    assert (
        second.headers.get_list("set-cookie")
        == first.headers.get_list("set-cookie")
        == ["layered=1; Path=/; SameSite=lax"]
    )


@pytest.mark.parametrize(
    "make_response",
    [
        lambda: Redirect("/elsewhere", status_code=HTTP_301_MOVED_PERMANENTLY),
        lambda: Response("", headers={"Location": "/a"}, status_code=HTTP_301_MOVED_PERMANENTLY),
    ],
)
def test_redirects_are_cached_with_location(mock: MagicMock, make_response: Callable[[], Response]) -> None:
    @get("/", cache=True, sync_to_thread=False)
    def handler() -> Response:
        mock()
        return make_response()

    with create_test_client([handler]) as client:
        first = client.get("/", follow_redirects=False)
        second = client.get("/", follow_redirects=False)

    assert mock.call_count == 1
    assert second.status_code == HTTP_301_MOVED_PERMANENTLY
    assert second.headers["location"] == first.headers["location"]


def test_returned_response_background_runs_on_miss_only(mock: MagicMock) -> None:
    task = MagicMock()

    @get("/", cache=True, sync_to_thread=False)
    def handler() -> Response[str]:
        mock()
        return Response("x", background=BackgroundTask(task))

    with create_test_client([handler]) as client:
        client.get("/")
        client.get("/")

    assert mock.call_count == 1
    assert task.call_count == 1


def test_after_request_runs_once_on_cached_routes(mock: MagicMock) -> None:
    def wrap(response: Response) -> Response:
        response.content = b"[" + response.content + b"]"
        return response

    @get("/", cache=True, sync_to_thread=False, after_request=wrap)
    def handler() -> list[int]:
        mock()
        return [1]

    with create_test_client([handler]) as client:
        first = client.get("/")
        second = client.get("/")

    assert first.text == second.text == "[[1]]"
    assert mock.call_count == 1


def test_layered_content_type_not_duplicated(mock: MagicMock) -> None:
    @get(
        "/",
        cache=True,
        sync_to_thread=False,
        response_headers=[ResponseHeader(name="Content-Type", value="application/vnd.api+json")],
    )
    def handler() -> dict[str, int]:
        mock()
        return {"a": 1}

    with create_test_client([handler]) as client:
        first = client.get("/")
        second = client.get("/")

    assert first.headers.get_list("content-type") == ["application/vnd.api+json"]
    assert second.headers.get_list("content-type") == ["application/vnd.api+json"]
    assert mock.call_count == 1


def test_background_task_runs_on_every_hit(mock: MagicMock) -> None:
    task = MagicMock()

    @get("/", cache=True, sync_to_thread=False, background=BackgroundTask(task))
    def handler() -> str:
        mock()
        return "ok"

    with create_test_client([handler]) as client:
        client.get("/")
        client.get("/")

    assert task.call_count == 2
    assert mock.call_count == 1


def test_custom_response_class_not_cached(mock: MagicMock) -> None:
    @get("/", cache=True, sync_to_thread=False, response_class=_RequestIdResponse)
    def handler() -> dict[str, int]:
        mock()
        return {"a": 1}

    with create_test_client([handler]) as client:
        first = client.get("/", headers={"x-request-id": "r1"})
        second = client.get("/", headers={"x-request-id": "r2"})

    assert mock.call_count == 2
    assert first.headers["x-request-id"] == "r1"
    assert second.headers["x-request-id"] == "r2"


def test_own_and_layered_headers_match_uncached_route(mock: MagicMock) -> None:
    def make(cache: bool) -> Any:
        @get(
            "/cached" if cache else "/uncached",
            cache=cache,
            sync_to_thread=False,
            response_headers=[
                ResponseHeader(name="Cache-Control", value="public"),
                ResponseHeader(name="x-a", value="layered"),
            ],
        )
        def handler() -> Response[str]:
            mock()
            return Response("x", headers={"cache-control": "no-store", "x-a": "own"})

        return handler

    with create_test_client([make(True), make(False)]) as client:
        expected = client.get("/uncached").headers
        first = client.get("/cached").headers
        second = client.get("/cached").headers

    for headers in (first, second):
        assert headers.get_list("cache-control") == expected.get_list("cache-control")
        assert headers.get_list("x-a") == expected.get_list("x-a") == ["own"]
    assert mock.call_count == 2


def test_shared_response_background_not_mutated() -> None:
    task = MagicMock()
    shared = Response("x", background=BackgroundTask(task))

    @get("/{value:str}", cache=True, sync_to_thread=False)
    def handler(value: FromPath[str]) -> Response[str]:
        return shared

    with create_test_client([handler]) as client:
        for value in ("a", "b", "c", "a"):
            client.get(f"/{value}")

    assert task.call_count == 3


def test_csrf_cookie_not_replayed() -> None:
    @get("/", cache=True, sync_to_thread=False)
    def handler() -> str:
        return "ok"

    app = Litestar([handler], csrf_config=CSRFConfig(secret="x" * 32))

    with TestClient(app) as client:
        first = client.get("/").cookies.get("csrftoken")
        client.cookies.clear()
        second = client.get("/").cookies.get("csrftoken")

    assert first
    assert second
    assert first != second


@pytest.mark.parametrize(
    ("make_response", "body"),
    [
        (lambda: Stream(iter([b"a", b"b"])), "ab"),
        (lambda: Response("x", cookies=[Cookie(key="a", value="b")]), "x"),
        (lambda: Response("x", headers={"Set-Cookie": "a=b"}), "x"),
        (lambda: _EnvelopeResponse("x"), '{"data":"x"}'),
        (lambda: Template(template_str="hello"), "hello"),
    ],
)
def test_uncacheable_responses_not_cached(
    mock: MagicMock, make_response: Callable[[], Response], body: str, tmp_path: Path
) -> None:
    @get("/", cache=True, sync_to_thread=False)
    def handler() -> Response:
        mock()
        return make_response()

    with create_test_client(
        [handler], template_config=TemplateConfig(directory=tmp_path, engine=JinjaTemplateEngine)
    ) as client:
        assert client.get("/").text == body
        assert client.get("/").text == body

    assert mock.call_count == 2


def test_asgi_response_not_cached(mock: MagicMock) -> None:
    @get("/", cache=True, sync_to_thread=False)
    def handler() -> ASGIResponse:
        mock()
        return ASGIResponse(body=b"x")

    with create_test_client([handler]) as client:
        assert client.get("/").text == "x"
        assert client.get("/").text == "x"

    assert mock.call_count == 2


@pytest.mark.parametrize(
    "make_response",
    [
        lambda: Redirect("/elsewhere"),
        lambda: Response("é", media_type="text/plain", encoding="latin-1"),
    ],
)
def test_cached_content_type_and_body_match_uncached(make_response: Callable[[], Response]) -> None:
    @get("/cached", cache=True, sync_to_thread=False)
    def cached() -> Response:
        return make_response()

    @get("/uncached", sync_to_thread=False)
    def uncached() -> Response:
        return make_response()

    with create_test_client([cached, uncached]) as client:
        expected = client.get("/uncached", follow_redirects=False)
        for _ in range(2):
            response = client.get("/cached", follow_redirects=False)
            assert response.headers["content-type"] == expected.headers["content-type"]
            assert response.content == expected.content


def test_not_cached_when_dependency_cleanup_fails(mock: MagicMock) -> None:
    cleanup = MagicMock(side_effect=[RuntimeError, None])

    async def dep() -> AsyncGenerator[None, None]:
        yield
        cleanup()

    @get("/", cache=True, sync_to_thread=False, dependencies={"d": Provide(dep)})
    def handler(d: NamedDependency[None]) -> str:
        mock()
        return "ok"

    with create_test_client([handler]) as client:
        assert [client.get("/").status_code for _ in range(3)] == [HTTP_500_INTERNAL_SERVER_ERROR, 200, 200]

    assert mock.call_count == 2


def test_cached_return_dto_body_matches(mock: MagicMock) -> None:
    @get(
        "/",
        cache=True,
        sync_to_thread=False,
        return_dto=DataclassDTO[Annotated[_User, DTOConfig(exclude={"secret"})]],
    )
    def handler() -> _User:
        mock()
        return _User(name="n", secret="s")

    with create_test_client([handler]) as client:
        first = client.get("/")
        second = client.get("/")

    assert first.json() == second.json() == {"name": "n"}
    assert second.headers["content-type"] == first.headers["content-type"]
    assert mock.call_count == 1


async def test_legacy_cache_entry_is_a_miss(mock: MagicMock) -> None:
    @get("/", cache=True, sync_to_thread=False)
    def handler() -> str:
        return mock()  # type: ignore[no-any-return]

    app = Litestar([handler])
    legacy = [
        {"type": "http.response.start", "status": 200, "headers": []},
        {"type": "http.response.body", "body": b"stale"},
    ]
    store = app.response_cache_config.get_store_from_app(app)
    await store.set("GET/", msgspec.msgpack.encode(legacy))

    with TestClient(app) as client:
        assert client.get("/").text == mock.return_value
        assert client.get("/").text == mock.return_value

    assert mock.call_count == 1
    assert await store.get("GET/") != msgspec.msgpack.encode(legacy)


def test_does_not_leak_state_between_sequential_requests() -> None:
    @get("/cached/{value:str}", cache=True)
    def handler(value: FromPath[str]) -> str:
        return value

    with create_test_client([handler]) as client:
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"
        assert client.get("/cached/first").text == "first"
        assert client.get("/cached/second").text == "second"


async def test_compression_applied_per_request_on_cached_route() -> None:
    return_value = "_litestar_" * 4000
    mock = MagicMock(return_value=return_value)

    @get(path="/", cache=True)
    def handler_fn() -> str:
        return mock()  # type: ignore[no-any-return]

    app = Litestar(route_handlers=[handler_fn], compression_config=CompressionConfig(backend="gzip"))

    with TestClient(app) as client:
        gzipped = client.get("/", headers={"Accept-Encoding": CompressionEncoding.GZIP.value})
        plain = client.get("/", headers={"Accept-Encoding": "identity"})

    assert mock.call_count == 1
    assert gzipped.headers["content-encoding"] == "gzip"
    assert "content-encoding" not in plain.headers
    assert plain.text == return_value


@pytest.mark.parametrize(
    ("response", "should_cache"),
    [
        (HTTP_200_OK, True),
        (HTTP_400_BAD_REQUEST, False),
        (HTTP_500_INTERNAL_SERVER_ERROR, False),
        (RuntimeError, False),
    ],
)
def test_default_do_response_cache_predicate(
    mock: MagicMock, response: Union[int, type[RuntimeError]], should_cache: bool
) -> None:
    @get("/", cache=True)
    def handler() -> Response[None]:
        mock()
        if isinstance(response, int):
            return Response(None, status_code=response)
        raise RuntimeError

    with create_test_client([handler]) as client:
        client.get("/")
        client.get("/")
        assert mock.call_count == (1 if should_cache else 2)


def test_custom_do_response_cache_predicate(mock: MagicMock) -> None:
    @get("/", cache=True)
    def handler() -> str:
        mock()
        return "OK"

    def filter_cache_response(_: HTTPScope, __: int) -> bool:
        return False

    with create_test_client(
        [handler], response_cache_config=ResponseCacheConfig(cache_response_filter=filter_cache_response)
    ) as client:
        client.get("/")
        client.get("/")
        assert mock.call_count == 2


def test_on_multiple_handlers(mock: MagicMock) -> None:
    @get("/cached-local", cache=10)
    async def handler() -> str:
        mock()
        return "get_response"

    @post("/cached-local", cache=10)
    async def handler_post() -> str:
        mock()
        return "post_response"

    with create_test_client([handler, handler_post], after_request=after_request_handler) as client:
        # POST request to have this cached
        first_post_response = client.post("/cached-local")
        assert first_post_response.status_code == HTTP_201_CREATED
        assert first_post_response.text == "post_response"
        assert mock.call_count == 1

        # GET request to verify it doesn't use the cache created by the previous POST request
        get_response = client.get("/cached-local")
        assert get_response.status_code == HTTP_200_OK
        assert get_response.text == "get_response"
        assert first_post_response.headers["unique-identifier"] != get_response.headers["unique-identifier"]
        assert mock.call_count == 2

        # POST request to verify it uses the cache generated during the initial POST request
        second_post_response = client.post("/cached-local")
        assert second_post_response.status_code == HTTP_201_CREATED
        assert second_post_response.text == "post_response"
        assert first_post_response.headers["unique-identifier"] != second_post_response.headers["unique-identifier"]
        assert mock.call_count == 2


def test_awaitable_return_value_is_cached(mock: MagicMock) -> None:
    async def value() -> str:
        return mock()  # type: ignore[no-any-return]

    @get("/", cache=True, sync_to_thread=False)
    def handler() -> Awaitable[str]:
        return value()

    with create_test_client([handler]) as client:
        assert client.get("/").text == mock.return_value
        assert client.get("/").text == mock.return_value

    assert mock.call_count == 1


def test_after_request_runs_before_dependency_cleanup_on_cached_route() -> None:
    events: list[str] = []

    async def dep() -> AsyncGenerator[None, None]:
        yield
        events.append("cleanup")

    def after(response: Response) -> Response:
        events.append("after_request")
        return response

    @get("/", cache=True, sync_to_thread=False, dependencies={"d": Provide(dep)}, after_request=after)
    def handler(d: NamedDependency[None]) -> str:
        return "ok"

    with create_test_client([handler]) as client:
        assert client.get("/").text == "ok"

    assert events == ["after_request", "cleanup"]
