from secrets import token_hex
from typing import TYPE_CHECKING

import pytest

from litestar import Litestar, Request, get, post
from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.serialization import encode_json
from litestar.stores.memory import MemoryStore
from litestar.testing import TestClient

if TYPE_CHECKING:
    from time_machine import Traveller

    from litestar.middleware.session.server_side import ServerSideSessionBackend


def generate_session_data() -> bytes:
    return encode_json({token_hex(): token_hex()})


@pytest.fixture
def session_data() -> bytes:
    return generate_session_data()


async def test_non_default_store(memory_store: MemoryStore) -> None:
    @get("/")
    def handler(request: Request) -> None:
        request.set_session({"foo": "bar"})
        return

    app = Litestar([handler], middleware=[ServerSideSessionConfig().middleware], stores={"sessions": memory_store})

    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert await memory_store.exists(res.cookies["session"])


async def test_set_store_name(memory_store: MemoryStore) -> None:
    @get("/")
    def handler(request: Request) -> None:
        request.set_session({"foo": "bar"})
        return

    app = Litestar(
        [handler],
        middleware=[ServerSideSessionConfig(store="some_store").middleware],
        stores={"some_store": memory_store},
    )

    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert await memory_store.exists(res.cookies["session"])


async def test_get_set(
    server_side_session_backend: "ServerSideSessionBackend", session_data: bytes, memory_store: MemoryStore
) -> None:
    await server_side_session_backend.set("foo", session_data, memory_store)
    loaded = await server_side_session_backend.get("foo", memory_store)

    assert loaded == session_data


async def test_get_renew_on_access(
    server_side_session_backend: "ServerSideSessionBackend",
    session_data: bytes,
    memory_store: MemoryStore,
    frozen_datetime: "Traveller",
) -> None:
    server_side_session_backend.config.max_age = 1
    server_side_session_backend.config.renew_on_access = True

    await server_side_session_backend.set("foo", session_data, memory_store)
    server_side_session_backend.config.max_age = 10

    await server_side_session_backend.get("foo", memory_store)

    frozen_datetime.shift(1.01)

    assert await server_side_session_backend.get("foo", memory_store) is not None


async def test_get_set_multiple_returns_correct_identity(
    server_side_session_backend: "ServerSideSessionBackend", memory_store: MemoryStore
) -> None:
    foo_data = generate_session_data()
    bar_data = generate_session_data()
    await server_side_session_backend.set("foo", foo_data, memory_store)
    await server_side_session_backend.set("bar", bar_data, memory_store)

    loaded = await server_side_session_backend.get("foo", memory_store)

    assert loaded == foo_data


async def test_delete(server_side_session_backend: "ServerSideSessionBackend", memory_store: MemoryStore) -> None:
    await server_side_session_backend.set("foo", generate_session_data(), memory_store)
    await server_side_session_backend.set("bar", generate_session_data(), memory_store)

    await server_side_session_backend.delete("foo", memory_store)

    assert not await server_side_session_backend.get("foo", memory_store)
    assert await server_side_session_backend.get("bar", memory_store)


async def test_delete_idempotence(
    server_side_session_backend: "ServerSideSessionBackend", session_data: bytes, memory_store: MemoryStore
) -> None:
    await server_side_session_backend.set("foo", session_data, memory_store)

    await server_side_session_backend.delete("foo", memory_store)
    await server_side_session_backend.delete("foo", memory_store)  # ensure this doesn't raise an error


async def test_max_age_expires(
    server_side_session_backend: "ServerSideSessionBackend",
    session_data: bytes,
    memory_store: MemoryStore,
    frozen_datetime: "Traveller",
) -> None:
    server_side_session_backend.config.max_age = 1
    await server_side_session_backend.set("foo", session_data, memory_store)

    frozen_datetime.shift(1)

    assert not await server_side_session_backend.get("foo", memory_store)


@pytest.mark.parametrize(
    "key, should_raise",
    [
        ["", True],
        ["a", False],
        ["a" * 256, False],
        ["a" * 257, True],
    ],
)
def test_key_validation(server_side_session_backend: "ServerSideSessionBackend", key: str, should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            ServerSideSessionConfig(key=key)
    else:
        ServerSideSessionConfig(key=key)


@pytest.mark.parametrize(
    "max_age, should_raise",
    [
        [0, True],
        [-1, True],
        [1, False],
        [100, False],
    ],
)
def test_max_age_validation(
    server_side_session_backend: "ServerSideSessionBackend", max_age: int, should_raise: bool
) -> None:
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            ServerSideSessionConfig(key="a", max_age=max_age)
    else:
        ServerSideSessionConfig(key="a", max_age=max_age)


@pytest.mark.parametrize("path", ["/unchanged", "/clear", "/clear-session"])
@pytest.mark.parametrize("cookies", [{}, {"session": "null"}])
async def test_empty_session_without_session_cookie_not_stored(
    path: str, cookies: dict[str, str], memory_store: MemoryStore
) -> None:
    # https://github.com/litestar-org/litestar/issues/5172
    @get("/unchanged")
    def unchanged_handler(request: Request) -> dict[str, str | None]:
        return {"session_id": request.get_session_id()}

    @get("/clear")
    def clear_handler(request: Request) -> dict[str, str | None]:
        session_id = request.get_session_id()
        request.session.clear()
        return {"session_id": session_id}

    @get("/clear-session")
    def clear_session_handler(request: Request) -> dict[str, str | None]:
        session_id = request.get_session_id()
        request.clear_session()
        return {"session_id": session_id}

    app = Litestar(
        [unchanged_handler, clear_handler, clear_session_handler],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": memory_store},
    )

    with TestClient(app, cookies=cookies) as client:
        res = client.get(path)
        assert res.status_code == 200
        assert "set-cookie" not in res.headers
        assert not await memory_store.exists(res.json()["session_id"])


@pytest.mark.parametrize("path", ["/clear", "/clear-session"])
async def test_cleared_session_with_session_cookie_deleted(path: str, memory_store: MemoryStore) -> None:
    # https://github.com/litestar-org/litestar/issues/5172
    @post("/login")
    def login_handler(request: Request) -> None:
        request.set_session({"foo": "bar"})

    @post("/clear")
    def clear_handler(request: Request) -> None:
        request.session.clear()

    @post("/clear-session")
    def clear_session_handler(request: Request) -> None:
        request.clear_session()

    app = Litestar(
        [login_handler, clear_handler, clear_session_handler],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": memory_store},
    )

    with TestClient(app) as client:
        session_id = client.post("/login").cookies["session"]
        assert await memory_store.exists(session_id)

        res = client.post(path)
        assert res.status_code == 201
        assert res.headers["set-cookie"].startswith("session=null;")
        assert not await memory_store.exists(session_id)


async def test_empty_session_with_unknown_session_cookie_not_stored(memory_store: MemoryStore) -> None:
    # https://github.com/litestar-org/litestar/issues/5172
    @get("/")
    def handler() -> None:
        return None

    app = Litestar([handler], middleware=[ServerSideSessionConfig().middleware], stores={"sessions": memory_store})

    with TestClient(app, cookies={"session": "unknown"}) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.headers["set-cookie"].startswith("session=null;")
        assert not await memory_store.exists("unknown")
