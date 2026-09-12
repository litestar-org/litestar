from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest

from litestar import Litestar, Request, get, websocket
from litestar.middleware.correlation import (
    TRACE_CONTEXT_FALLBACK_HEADERS,
    CorrelationMiddleware,
    get_correlation_id,
)
from litestar.params import FromPath
from litestar.testing import AsyncTestClient

if TYPE_CHECKING:
    from litestar.connection import WebSocket
    from litestar.types import Message, Receive, Scope, Send


async def _receive() -> Any:
    return {"type": "http.request"}


async def _send(_: Message) -> None:
    return None


def _scope(scope_type: str = "http", headers: list[tuple[bytes, bytes]] | None = None) -> Any:
    return {"type": scope_type, "headers": headers or []}


def test_header_names_are_normalized_and_deduplicated() -> None:
    middleware = CorrelationMiddleware(header_names=[" X-Request-ID ", "x-request-id", "X-Trace-ID"])
    assert middleware.header_names == ("x-request-id", "x-trace-id")


def test_default_header_names_are_conservative() -> None:
    assert TRACE_CONTEXT_FALLBACK_HEADERS == ("x-request-id", "x-correlation-id", "traceparent")
    assert CorrelationMiddleware().header_names == TRACE_CONTEXT_FALLBACK_HEADERS


def test_additional_header_names_extend_defaults() -> None:
    middleware = CorrelationMiddleware(additional_header_names=("grpc-trace-bin", " X-Request-ID "))
    assert middleware.header_names == (*TRACE_CONTEXT_FALLBACK_HEADERS, "grpc-trace-bin")


def test_single_additional_header_name_is_not_treated_as_a_sequence_of_characters() -> None:
    middleware = CorrelationMiddleware(additional_header_names="grpc-trace-bin")
    assert middleware.header_names == (*TRACE_CONTEXT_FALLBACK_HEADERS, "grpc-trace-bin")


def test_header_names_and_additional_header_names_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="header_names and additional_header_names are mutually exclusive"):
        CorrelationMiddleware(header_names=("x-custom-id",), additional_header_names=("grpc-trace-bin",))


async def test_single_header_name_is_not_treated_as_a_sequence_of_characters() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert get_correlation_id(scope) == "selected"

    middleware = CorrelationMiddleware(header_names="X-Correlation-ID")
    scope = _scope(headers=[(b"x-correlation-id", b"selected")])
    await middleware(app)(scope, _receive, _send)


@pytest.mark.parametrize("max_length", [0, -1])
def test_max_length_must_be_positive(max_length: int) -> None:
    with pytest.raises(ValueError, match="max_length must be greater than 0"):
        CorrelationMiddleware(max_length=max_length)


@pytest.mark.parametrize("unsafe_value", [b"", b"   ", b"bad\x00id", b"bad\x1fid", b"bad\x7fid", b"bad\tid"])
async def test_blank_or_control_character_values_fall_through_to_lower_priority_header(unsafe_value: bytes) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert get_correlation_id(scope) == "safe-id"

    middleware = CorrelationMiddleware(header_names=["x-first", "x-second"])
    scope = _scope(headers=[(b"x-first", unsafe_value), (b"x-second", b"safe-id")])
    await middleware(app)(scope, _receive, _send)


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
async def test_malformed_traceparent_uses_sanitized_raw_value(value: str) -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert get_correlation_id(scope) == value[:128]

    scope = _scope(headers=[(b"traceparent", f"  {value}  ".encode())])
    await CorrelationMiddleware(header_names="traceparent")(app)(scope, _receive, _send)


async def test_valid_traceparent_extracts_trace_id() -> None:
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert get_correlation_id(scope) == trace_id

    scope = _scope(headers=[(b"traceparent", f"00-{trace_id}-00f067aa012302b7-01".encode())])
    await CorrelationMiddleware(header_names="traceparent")(app)(scope, _receive, _send)


async def test_traceparent_is_validated_before_max_length_is_applied() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert get_correlation_id(scope) == "4bf92f35"

    value = b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa012302b7-01"
    scope = _scope(headers=[(b"traceparent", value)])
    await CorrelationMiddleware(header_names="traceparent", max_length=8)(app)(scope, _receive, _send)


async def test_unsafe_traceparent_falls_through_to_lower_priority_header() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert get_correlation_id(scope) == "safe-id"

    scope = _scope(headers=[(b"traceparent", b"bad\tvalue"), (b"x-request-id", b"safe-id")])
    middleware = CorrelationMiddleware(header_names=["traceparent", "x-request-id"])
    await middleware(app)(scope, _receive, _send)


async def test_uuid_is_generated_when_no_safe_header_matches() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        correlation_id = get_correlation_id(scope)
        assert correlation_id is not None
        assert UUID(correlation_id)

    scope = _scope(headers=[(b"x-request-id", b"bad\nvalue")])
    await CorrelationMiddleware()(app)(scope, _receive, _send)


def test_get_correlation_id_returns_none_when_middleware_did_not_run() -> None:
    assert get_correlation_id(_scope()) is None


async def test_explicit_grpc_trace_header_is_opaque_and_unchanged() -> None:
    value = b"opaque-grpc-trace-value"

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        assert get_correlation_id(scope) == value.decode()
        assert scope["headers"] == [(b"grpc-trace-bin", value)]

    scope = _scope(headers=[(b"grpc-trace-bin", value)])
    await CorrelationMiddleware(header_names="grpc-trace-bin")(app)(scope, _receive, _send)


async def test_response_header_replaces_existing_values() -> None:
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
    await CorrelationMiddleware()(app)(scope, _receive, send)
    assert sent[0]["headers"] == [(b"x-request-id", b"authoritative")]


async def test_response_header_can_be_disabled() -> None:
    sent: list[Any] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})

    async def send(message: Message) -> None:
        sent.append(message)

    scope = _scope()
    await CorrelationMiddleware(response_header_name=None)(app)(scope, _receive, send)
    assert sent[0]["headers"] == []


async def test_correlation_id_is_available_to_downstream_middleware_and_handlers() -> None:
    async def downstream(scope: Scope, receive: Receive, send: Send, next_app: Any) -> None:
        assert get_correlation_id(scope) == "shared-id"
        await next_app(scope, receive, send)

    from litestar.middleware.base import ASGIMiddleware

    class DownstreamMiddleware(ASGIMiddleware):
        async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: Any) -> None:
            await downstream(scope, receive, send, next_app)

    @get("/")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, str | None]:
        return {"correlation_id": get_correlation_id(request)}

    app = Litestar(route_handlers=[handler], middleware=[CorrelationMiddleware(), DownstreamMiddleware()])
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/", headers={"x-request-id": "shared-id"})
    assert response.json() == {"correlation_id": "shared-id"}
    assert response.headers["x-request-id"] == "shared-id"


async def test_http_requests_are_isolated_concurrently() -> None:
    @get("/{request_id:str}")
    async def handler(request: Request[Any, Any, Any], request_id: FromPath[str]) -> dict[str, str | None]:
        await asyncio.sleep(0)
        return {"correlation_id": get_correlation_id(request), "request_id": request_id}

    app = Litestar(route_handlers=[handler], middleware=[CorrelationMiddleware()])
    async with AsyncTestClient(app=app) as client:
        responses = await asyncio.gather(
            *(client.get(f"/{index}", headers={"x-request-id": f"id-{index}"}) for index in range(10))
        )
    assert [response.json()["correlation_id"] for response in responses] == [f"id-{index}" for index in range(10)]


async def test_websocket_scope_exposes_correlation_id() -> None:
    @websocket("/")
    async def handler(socket: WebSocket[Any, Any, Any]) -> None:
        await socket.accept()
        await socket.send_text(get_correlation_id(socket) or "missing")
        await socket.close()

    app = Litestar(route_handlers=[handler], middleware=[CorrelationMiddleware()])
    async with AsyncTestClient(app=app) as client:
        async with await client.websocket_connect("/", headers={"x-request-id": "websocket-id"}) as socket:
            assert await socket.receive_text() == "websocket-id"
