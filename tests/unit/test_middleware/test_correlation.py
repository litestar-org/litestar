from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest

from litestar import Litestar, get, websocket
from litestar.middleware.correlation import CorrelationContext, CorrelationMiddleware
from litestar.params import FromPath
from litestar.testing import AsyncTestClient

if TYPE_CHECKING:
    from litestar.connection import WebSocket
    from litestar.types import Message, Receive, Scope, Send


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _receive() -> Any:
    return {"type": "http.request"}


async def _send(_: Message) -> None:
    return None


def _scope(
    scope_type: str = "http", headers: list[tuple[bytes, bytes]] | None = None, state: dict[str, Any] | None = None
) -> Any:
    scope: dict[str, Any] = {"type": scope_type, "headers": headers or []}
    if state is not None:
        scope["state"] = state
    return scope


def test_correlation_context_operations() -> None:
    token = CorrelationContext.set("outer")
    try:
        with CorrelationContext.context("inner") as correlation_id:
            assert correlation_id == "inner"
            assert CorrelationContext.get() == "inner"
        assert CorrelationContext.get() == "outer"

        with CorrelationContext.context() as generated:
            assert UUID(generated)

        CorrelationContext.clear()
        assert CorrelationContext.get() is None
    finally:
        CorrelationContext.reset(token)


def test_header_names_are_normalized_and_deduplicated() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = CorrelationMiddleware(app, header_names=[" X-Request-ID ", "x-request-id", "X-Trace-ID"])
    assert middleware.header_names == ("x-request-id", "x-trace-id")


def test_single_header_name_is_not_treated_as_a_sequence_of_characters() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == "selected"

    middleware = CorrelationMiddleware(app, header_names="X-Correlation-ID")
    scope = _scope(headers=[(b"x-correlation-id", b"selected")])
    asyncio.run(middleware(scope, _receive, _send))


@pytest.mark.parametrize("max_length", [0, -1])
def test_max_length_must_be_positive(max_length: int) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    with pytest.raises(ValueError, match="max_length must be greater than 0"):
        CorrelationMiddleware(app, max_length=max_length)


@pytest.mark.parametrize("unsafe_value", [b"", b"   ", b"bad\x00id", b"bad\x1fid", b"bad\x7fid", b"bad\tid"])
def test_blank_or_control_character_values_fall_through_to_lower_priority_header(unsafe_value: bytes) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == "safe-id"

    middleware = CorrelationMiddleware(app, header_names=["x-first", "x-second"])
    scope = _scope(headers=[(b"x-first", unsafe_value), (b"x-second", b"safe-id")])
    asyncio.run(middleware(scope, _receive, _send))


def test_reads_raw_scope_headers_after_downstream_header_cache_was_created() -> None:
    from litestar.datastructures.headers import Headers

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == "mutated"

    scope = _scope(headers=[(b"x-request-id", b"original")])
    assert Headers.from_scope(scope)["x-request-id"] == "original"
    scope["headers"] = [(b"x-request-id", b"mutated")]
    asyncio.run(CorrelationMiddleware(app)(scope, _receive, _send))


@pytest.mark.parametrize(
    "value",
    [
        "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa012302b7-01",
        "0-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa012302b7-01",
        "0G-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa012302b7-01",
        "00-4BF92F3577B34DA6A3CE929D0E0E4736-00f067aa012302b7-01",
        "00-00000000000000000000000000000000-00f067aa012302b7-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00F067AA012302B7-01",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa012302b7-0G",
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa012302b7-01-extra",
    ],
)
def test_malformed_traceparent_uses_sanitized_raw_value(value: str) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == value[:128]

    scope = _scope(headers=[(b"traceparent", f"  {value}  ".encode())])
    asyncio.run(CorrelationMiddleware(app, header_names="traceparent")(scope, _receive, _send))


def test_valid_traceparent_extracts_trace_id() -> None:
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == trace_id

    scope = _scope(headers=[(b"traceparent", f"00-{trace_id}-00f067aa012302b7-01".encode())])
    asyncio.run(CorrelationMiddleware(app, header_names="traceparent")(scope, _receive, _send))


def test_traceparent_is_validated_before_max_length_is_applied() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == "4bf92f35"

    value = b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa012302b7-01"
    scope = _scope(headers=[(b"traceparent", value)])
    asyncio.run(CorrelationMiddleware(app, header_names="traceparent", max_length=8)(scope, _receive, _send))


def test_unsafe_traceparent_falls_through_to_lower_priority_header() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == "safe-id"

    scope = _scope(headers=[(b"traceparent", b"bad\tvalue"), (b"x-request-id", b"safe-id")])
    middleware = CorrelationMiddleware(app, header_names=["traceparent", "x-request-id"])
    asyncio.run(middleware(scope, _receive, _send))


def test_uuid_is_generated_when_no_safe_header_matches() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        correlation_id = CorrelationContext.get()
        assert correlation_id is not None
        assert UUID(correlation_id)

    scope = _scope(headers=[(b"x-request-id", b"bad\nvalue")])
    asyncio.run(CorrelationMiddleware(app)(scope, _receive, _send))


def test_response_header_replaces_existing_values() -> None:
    sent: list[Any] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"x-request-id", b"old-one"), (b"X-Request-ID", b"old-two")],
            }
        )

    async def send(message: Message) -> None:
        sent.append(message)

    scope = _scope(headers=[(b"x-request-id", b"authoritative")])
    asyncio.run(CorrelationMiddleware(app)(scope, _receive, send))
    assert sent[0]["headers"] == [(b"x-request-id", b"authoritative")]


def test_response_header_can_be_disabled() -> None:
    sent: list[Any] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})

    async def send(message: Message) -> None:
        sent.append(message)

    scope = _scope()
    asyncio.run(CorrelationMiddleware(app, response_header_name=None)(scope, _receive, send))
    assert sent[0]["headers"] == []


@pytest.mark.parametrize("raises", [False, True])
def test_context_and_prior_scope_state_are_restored(raises: bool) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert CorrelationContext.get() == "request-id"
        assert scope["state"]["correlation_id"] == "request-id"
        if raises:
            raise RuntimeError("boom")

    token = CorrelationContext.set("outer-id")
    scope = _scope(headers=[(b"x-request-id", b"request-id")], state={"correlation_id": "prior-state"})
    try:
        if raises:
            with pytest.raises(RuntimeError, match="boom"):
                asyncio.run(CorrelationMiddleware(app)(scope, _receive, _send))
        else:
            asyncio.run(CorrelationMiddleware(app)(scope, _receive, _send))
        assert CorrelationContext.get() == "outer-id"
        assert scope["state"]["correlation_id"] == "prior-state"
    finally:
        CorrelationContext.reset(token)


def test_new_scope_state_value_is_removed_on_unwind() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert "correlation_id" in scope["state"]

    scope = _scope(scope_type="websocket", state={})
    asyncio.run(CorrelationMiddleware(app)(scope, _receive, _send))
    assert "correlation_id" not in scope["state"]


def test_non_request_scope_is_bypassed() -> None:
    called = False

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal called
        called = True
        assert CorrelationContext.get() is None
        assert "state" not in scope

    scope = _scope(scope_type="lifespan")
    scope.pop("headers")
    asyncio.run(CorrelationMiddleware(app)(scope, _receive, _send))
    assert called


@pytest.mark.anyio
async def test_http_requests_are_isolated_concurrently() -> None:
    @get("/{request_id:str}")
    async def handler(request_id: FromPath[str]) -> dict[str, str | None]:
        await asyncio.sleep(0)
        return {"correlation_id": CorrelationContext.get(), "request_id": request_id}

    app = Litestar(route_handlers=[handler], middleware=[CorrelationMiddleware])
    async with AsyncTestClient(app=app) as client:
        responses = await asyncio.gather(
            *(client.get(f"/{index}", headers={"x-request-id": f"id-{index}"}) for index in range(10))
        )
    assert [response.json()["correlation_id"] for response in responses] == [f"id-{index}" for index in range(10)]


@pytest.mark.anyio
async def test_websocket_scope_exposes_correlation_context() -> None:
    @websocket("/")
    async def handler(socket: WebSocket[Any, Any, Any]) -> None:
        await socket.accept()
        await socket.send_text(CorrelationContext.get() or "missing")
        await socket.close()

    app = Litestar(route_handlers=[handler], middleware=[CorrelationMiddleware])
    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/", headers={"x-request-id": "websocket-id"}) as socket:
            assert await socket.receive_text() == "websocket-id"
