# pyright: reportUnnecessaryTypeIgnoreComment=false

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from _pytest.fixtures import FixtureRequest
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics._internal import MeterProvider
from opentelemetry.sdk.metrics._internal.aggregation import (
    ExplicitBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.export import InMemoryMetricReader
from opentelemetry.sdk.metrics._internal.instrument import Counter
from opentelemetry.sdk.metrics.export import Histogram
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import Span as SdkSpan
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, SpanKind
from pytest_mock import MockerFixture

from litestar import Litestar, Router, WebSocket, asgi, get, websocket
from litestar.config.app import AppConfig
from litestar.enums import ScopeType
from litestar.exceptions import http_exceptions
from litestar.params import FromPath, JSONBody
from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
from litestar.plugins.opentelemetry._utils import get_route_details_from_scope
from litestar.response.base import ASGIResponse
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient, create_test_client
from litestar.types.asgi_types import ASGIApp, Receive, Scope, Send


@pytest.fixture(scope="session")
def resource() -> Resource:
    return Resource(attributes={SERVICE_NAME: "litestar-test"})


@pytest.fixture(scope="session")
def reader() -> InMemoryMetricReader:
    aggregation_last_value = {Counter: ExplicitBucketHistogramAggregation(boundaries=[])}
    return InMemoryMetricReader(preferred_aggregation=aggregation_last_value)  # type: ignore[arg-type]


@pytest.fixture(scope="session")
def meter_provider(resource: Resource, reader: InMemoryMetricReader) -> MeterProvider:
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    set_meter_provider(provider)
    return provider


@pytest.fixture()
def exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture()
def config(
    resource: Resource, exporter: InMemorySpanExporter, meter_provider: MeterProvider, request: FixtureRequest
) -> OpenTelemetryConfig:
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    meter = get_meter_provider().get_meter(f"litestar-test-{request.node.nodeid}")
    return OpenTelemetryConfig(tracer_provider=tracer_provider, meter=meter)


@pytest.fixture(params=["middleware", "plugin"])
def app_config(request: FixtureRequest, config: OpenTelemetryConfig) -> AppConfig:
    if request.param == "middleware":
        return AppConfig(middleware=[config.middleware])
    return AppConfig(plugins=[OpenTelemetryPlugin(config)])


def test_open_telemetry_middleware_with_http_route(
    app_config: AppConfig,
    reader: InMemoryMetricReader,
    exporter: InMemorySpanExporter,
) -> None:
    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, middleware=app_config.middleware, plugins=app_config.plugins) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert reader.get_metrics_data()

        first_span, second_span, third_span = cast("tuple[SdkSpan, SdkSpan, SdkSpan]", exporter.get_finished_spans())
        assert dict(first_span.attributes) == {"http.status_code": 200, "asgi.event.type": "http.response.start"}  # type: ignore[arg-type]
        assert dict(second_span.attributes) == {"asgi.event.type": "http.response.body"}  # type: ignore[arg-type]
        assert dict(third_span.attributes) == {  # type: ignore[arg-type]
            "http.scheme": "http",
            "http.host": "testserver.local",
            "net.host.port": 80,
            "http.flavor": "1.1",
            "http.target": "/",
            "http.url": "http://testserver.local/",
            "http.method": "GET",
            "http.server_name": "testserver.local",
            "http.user_agent": "testclient",
            "net.peer.ip": "testclient",
            "net.peer.port": 50000,
            "http.route": "/",
            "http.status_code": 200,
        }
        assert third_span.name == "GET /"

        metric_data = reader.get_metrics_data()
        assert metric_data
        assert metric_data.resource_metrics

        resource_metrics = metric_data.resource_metrics[0]
        assert resource_metrics.scope_metrics

        scope_metrics = next(sm for sm in resource_metrics.scope_metrics if sm.scope.name != "opentelemetry-sdk")
        assert scope_metrics.metrics

        request_metric = scope_metrics.metrics[0]
        assert len(list(request_metric.data.data_points)) == 1


def test_open_telemetry_middleware_with_websocket_route(
    app_config: AppConfig,
    exporter: InMemorySpanExporter,
) -> None:
    @websocket("/ws/{room_id:str}")
    async def handler(socket: "WebSocket", room_id: FromPath[str]) -> None:
        await socket.accept()
        await socket.send_json(room_id)
        await socket.close()

    with create_test_client(handler, middleware=app_config.middleware, plugins=app_config.plugins) as client:
        with client.websocket_connect("/ws/general") as ws_client:
            assert ws_client.receive_json() == "general"

        first_span, second_span, third_span, fourth_span, fifth_span = cast(
            "tuple[SdkSpan, SdkSpan, SdkSpan, SdkSpan, SdkSpan]", exporter.get_finished_spans()
        )
        assert dict(first_span.attributes) == {"asgi.event.type": "websocket.connect"}  # type: ignore[arg-type]
        assert dict(second_span.attributes) == {"asgi.event.type": "websocket.accept"}  # type: ignore[arg-type]
        assert dict(third_span.attributes) == {"asgi.event.type": "websocket.send", "http.status_code": 200}  # type: ignore[arg-type]
        assert dict(fourth_span.attributes) == {"asgi.event.type": "websocket.close"}  # type: ignore[arg-type]
        assert dict(fifth_span.attributes) == {  # type: ignore[arg-type]
            "http.scheme": "ws",
            "http.host": "testserver.local",
            "net.host.port": 80,
            "http.target": "/ws/general",
            "http.url": "ws://testserver.local/ws/general",
            "http.server_name": "testserver.local",
            "http.user_agent": "testclient",
            "net.peer.ip": "testclient",
            "net.peer.port": 50000,
            "http.route": "/ws/{room_id}",
            "http.status_code": 200,
        }
        assert fifth_span.name == "/ws/{room_id}"


def test_open_telemetry_middleware_handles_route_not_found_under_span_http(
    app_config: AppConfig,
    exporter: InMemorySpanExporter,
) -> None:
    @get("/")
    def handler() -> dict:
        raise Exception("random Exception")

    with create_test_client(handler, middleware=app_config.middleware, plugins=app_config.plugins) as client:
        response = client.get("/route_that_does_not_exist")
        assert response.status_code == 404

        first_span, second_span, third_span = cast("tuple[SdkSpan, SdkSpan, SdkSpan]", exporter.get_finished_spans())
        assert dict(first_span.attributes) == {  # type: ignore[arg-type]
            "http.status_code": 404,
            "asgi.event.type": "http.response.start",
        }
        assert dict(second_span.attributes) == {"asgi.event.type": "http.response.body"}  # type: ignore[arg-type]
        assert dict(third_span.attributes) == {  # type: ignore[arg-type]
            "http.scheme": "http",
            "http.host": "testserver.local",
            "net.host.port": 80,
            "http.flavor": "1.1",
            "http.target": "/route_that_does_not_exist",
            "http.url": "http://testserver.local/route_that_does_not_exist",
            "http.method": "GET",
            "http.server_name": "testserver.local",
            "http.user_agent": "testclient",
            "net.peer.ip": "testclient",
            "net.peer.port": 50000,
            "http.status_code": 404,
        }
        assert third_span.name == "GET"


def test_open_telemetry_middleware_handles_method_not_allowed_under_span_http(
    app_config: AppConfig,
    exporter: InMemorySpanExporter,
) -> None:
    @get("/")
    def handler() -> dict:
        raise Exception("random Exception")

    with create_test_client(handler, middleware=app_config.middleware, plugins=app_config.plugins) as client:
        response = client.post("/")
        assert response.status_code == 405

        first_span, second_span, third_span = cast("tuple[SdkSpan, SdkSpan, SdkSpan]", exporter.get_finished_spans())
        assert dict(first_span.attributes) == {  # type: ignore[arg-type]
            "http.status_code": 405,
            "asgi.event.type": "http.response.start",
        }
        assert dict(second_span.attributes) == {"asgi.event.type": "http.response.body"}  # type: ignore[arg-type]
        assert dict(third_span.attributes) == {  # type: ignore[arg-type]
            "http.scheme": "http",
            "http.host": "testserver.local",
            "net.host.port": 80,
            "http.flavor": "1.1",
            "http.target": "/",
            "http.url": "http://testserver.local/",
            "http.method": "POST",
            "http.server_name": "testserver.local",
            "http.user_agent": "testclient",
            "net.peer.ip": "testclient",
            "net.peer.port": 50000,
            "http.status_code": 405,
        }
        assert third_span.name == "POST"


@pytest.mark.parametrize("method, expected_name", [("GET", "GET /"), ("FOO", "HTTP /")])
def test_span_details_sanitize_method(scope: Scope, method: str, expected_name: str) -> None:
    cast("dict[str, Any]", scope)["method"] = method
    scope["path_template"] = "/"
    assert get_route_details_from_scope(scope) == (expected_name, {"http.route": "/"})


def test_open_telemetry_middleware_handles_errors_caused_on_middleware(
    app_config: AppConfig,
    reader: InMemoryMetricReader,
    exporter: InMemorySpanExporter,
) -> None:
    raise_exception = True

    def middleware_factory(app: ASGIApp) -> ASGIApp:
        async def error_middleware(scope: Scope, receive: Receive, send: Send) -> None:
            if raise_exception:
                raise http_exceptions.NotAuthorizedException()
            await app(scope, receive, send)

        return error_middleware

    @get("/")
    def handler() -> dict:
        raise Exception("random Exception")

    with create_test_client(
        handler, middleware=[middleware_factory, *app_config.middleware], plugins=app_config.plugins
    ) as client:
        response = client.get("/")
        assert response.status_code

        first_span, second_span, third_span = cast("tuple[SdkSpan, SdkSpan, SdkSpan]", exporter.get_finished_spans())
        assert dict(first_span.attributes) == {  # type: ignore[arg-type]
            "http.status_code": 401,
            "asgi.event.type": "http.response.start",
        }
        assert dict(second_span.attributes) == {"asgi.event.type": "http.response.body"}  # type: ignore[arg-type]
        assert dict(third_span.attributes) == {  # type: ignore[arg-type]
            "http.scheme": "http",
            "http.host": "testserver.local",
            "net.host.port": 80,
            "http.flavor": "1.1",
            "http.target": "/",
            "http.url": "http://testserver.local/",
            "http.method": "GET",
            "http.server_name": "testserver.local",
            "http.user_agent": "testclient",
            "net.peer.ip": "testclient",
            "net.peer.port": 50000,
            "http.route": "/",
            "http.status_code": 401,
        }
        assert third_span.name == "GET /"


def test_after_exception_hook_handler_called_on_exception(
    resource: Resource, exporter: InMemorySpanExporter, meter_provider: MeterProvider, request: FixtureRequest
) -> None:
    """Test that after_exception_hook_handler is called when an exception occurs."""
    # Track calls to the hook
    hook_calls: list[tuple[Exception, Scope]] = []

    def after_exception_hook(exc: Exception, scope: Scope) -> None:
        hook_calls.append((exc, scope))

    # Create config with the hook handler
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    meter = get_meter_provider().get_meter(f"litestar-test-{request.node.nodeid}")
    config = OpenTelemetryConfig(
        tracer_provider=tracer_provider, meter=meter, after_exception_hook_handler=after_exception_hook
    )

    test_exception = ValueError("test error")

    @get("/")
    def handler() -> dict:
        raise test_exception

    with create_test_client(handler, plugins=[OpenTelemetryPlugin(config)]) as client:
        response = client.get("/")
        assert response.status_code == 500

        # Verify the hook was called exactly once
        assert len(hook_calls) == 1
        exc, scope = hook_calls[0]

        # Verify the exception is the one we raised
        assert exc is test_exception
        assert isinstance(exc, ValueError)
        assert str(exc) == "test error"

        # Verify the scope is provided
        assert scope is not None
        assert scope["type"] == ScopeType.HTTP
        assert scope["path"] == "/"
        assert scope["method"] == "GET"


def test_after_exception_hook_handler_not_called_on_success(
    resource: Resource, exporter: InMemorySpanExporter, meter_provider: MeterProvider, request: FixtureRequest
) -> None:
    """Test that after_exception_hook_handler is not called when no exception occurs."""
    # Track calls to the hook
    hook_calls: list[tuple[Exception, Scope]] = []

    def after_exception_hook(exc: Exception, scope: Scope) -> None:
        hook_calls.append((exc, scope))

    # Create config with the hook handler
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    meter = get_meter_provider().get_meter(f"litestar-test-{request.node.nodeid}")
    config = OpenTelemetryConfig(
        tracer_provider=tracer_provider, meter=meter, after_exception_hook_handler=after_exception_hook
    )

    @get("/")
    def handler() -> dict:
        return {"success": True}

    with create_test_client(handler, plugins=[OpenTelemetryPlugin(config)]) as client:
        response = client.get("/")
        assert response.status_code == 200

        # Verify the hook was NOT called
        assert len(hook_calls) == 0


def test_exclude_opt_key_no_keyerror_without_route_handler(
    config: OpenTelemetryConfig,
    reader: InMemoryMetricReader,
    exporter: InMemorySpanExporter,
) -> None:
    """Test #4468: should_bypass_middleware does not KeyError when route_handler not in scope.

    OTEL middleware runs as outermost middleware, before the ASGI router populates
    scope["route_handler"]. With exclude_opt_key set, the old code would raise KeyError.
    """
    config.exclude_opt_key = "skip_otel"

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, plugins=[OpenTelemetryPlugin(config)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK


def test_client_request_hook_receives_three_params(
    resource: Resource, exporter: InMemorySpanExporter, meter_provider: MeterProvider, request: FixtureRequest
) -> None:
    """Test #4466: client_request_hook receives (span, scope, message) — 3 params, not 2.

    The client_request_hook fires when receive() is called, so we need a POST handler
    that reads the request body to trigger it.
    """
    from litestar import post

    hook_calls: list[tuple] = []

    def client_request_hook(span: "Span", scope: "dict[str, Any]", message: "dict[str, Any]") -> None:
        hook_calls.append((span, scope, message))

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    meter = get_meter_provider().get_meter(f"litestar-test-{request.node.nodeid}")
    config = OpenTelemetryConfig(
        tracer_provider=tracer_provider,
        meter=meter,
        client_request_hook_handler=client_request_hook,
    )

    @post("/")
    async def handler(data: JSONBody[dict]) -> dict:
        return data

    with create_test_client(handler, plugins=[OpenTelemetryPlugin(config)]) as client:
        response = client.post("/", json={"key": "value"})
        assert response.status_code == 201

        # The hook fires on receive() calls — with 3 args (span, scope_dict, message_dict)
        assert len(hook_calls) >= 1
        for call in hook_calls:
            assert len(call) == 3
            span, scope_dict, message_dict = call
            assert isinstance(span, Span)
            assert isinstance(scope_dict, dict)
            assert isinstance(message_dict, dict)


def test_client_response_hook_receives_three_params(
    resource: Resource, exporter: InMemorySpanExporter, meter_provider: MeterProvider, request: FixtureRequest
) -> None:
    """Test #4466: client_response_hook receives (span, scope, message) — 3 params, not 2."""
    hook_calls: list[tuple] = []

    def client_response_hook(span: "Span", scope: "dict[str, Any]", message: "dict[str, Any]") -> None:
        hook_calls.append((span, scope, message))

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    meter = get_meter_provider().get_meter(f"litestar-test-{request.node.nodeid}")
    config = OpenTelemetryConfig(
        tracer_provider=tracer_provider,
        meter=meter,
        client_response_hook_handler=client_response_hook,
    )

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, plugins=[OpenTelemetryPlugin(config)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        assert len(hook_calls) >= 1
        for call in hook_calls:
            assert len(call) == 3
            span, scope_dict, message_dict = call
            assert isinstance(span, Span)
            assert isinstance(scope_dict, dict)
            assert isinstance(message_dict, dict)


def test_server_request_hook_receives_two_params(
    resource: Resource, exporter: InMemorySpanExporter, meter_provider: MeterProvider, request: FixtureRequest
) -> None:
    """Verify server_request_hook still receives (span, scope) — 2 params."""
    hook_calls: list[tuple] = []

    def server_request_hook(span: "Span", scope: "dict[str, Any]") -> None:
        hook_calls.append((span, scope))

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    meter = get_meter_provider().get_meter(f"litestar-test-{request.node.nodeid}")
    config = OpenTelemetryConfig(
        tracer_provider=tracer_provider,
        meter=meter,
        server_request_hook_handler=server_request_hook,
    )

    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client(handler, plugins=[OpenTelemetryPlugin(config)]) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        assert len(hook_calls) == 1
        span, scope_dict = hook_calls[0]
        assert isinstance(span, Span)
        assert isinstance(scope_dict, dict)


def test_new_config_params_accepted() -> None:
    """Test upstream parity: new config params are accepted without error."""
    config = OpenTelemetryConfig(
        http_capture_headers_server_request=["content-type", "x-request-id"],
        http_capture_headers_server_response=["content-type"],
        http_capture_headers_sanitize_fields=["authorization", "cookie"],
    )
    assert config.http_capture_headers_server_request == ["content-type", "x-request-id"]
    assert config.http_capture_headers_server_response == ["content-type"]
    assert config.http_capture_headers_sanitize_fields == ["authorization", "cookie"]


def test_tracer_config_param_accepted() -> None:
    """Test upstream parity: tracer param is accepted."""
    from opentelemetry.trace import get_tracer

    tracer = get_tracer("test")
    config = OpenTelemetryConfig(tracer=tracer)
    assert config.tracer is tracer


@pytest.mark.parametrize("root_path", ["", "/api/v1"])
def test_parameterized_http_route(
    config: OpenTelemetryConfig, app_config: AppConfig, exporter: InMemorySpanExporter, root_path: str
) -> None:
    hook_templates: list[str] = []
    config.server_request_hook_handler = lambda span, scope: hook_templates.append(scope["path_template"])

    @get("/articles/{article_id:int}")
    async def handler(article_id: FromPath[int]) -> int:
        return article_id

    with create_test_client(
        handler, middleware=app_config.middleware, plugins=app_config.plugins, root_path=root_path
    ) as client:
        assert client.get(f"{root_path}/articles/9041").json() == 9041

    server_span = next(span for span in exporter.get_finished_spans() if span.kind == SpanKind.SERVER)
    assert server_span.name == "GET /articles/{article_id}"
    assert server_span.attributes is not None
    assert server_span.attributes["http.route"] == "/articles/{article_id}"
    assert hook_templates == ["/articles/{article_id}"]


def test_middleware_on_handlers_and_routers(config: OpenTelemetryConfig, exporter: InMemorySpanExporter) -> None:
    @get("/articles/{article_id:int}", middleware=[config.middleware])
    async def handler(article_id: FromPath[int]) -> int:
        return article_id

    @get("/items/{item_id:int}")
    async def router_handler(item_id: FromPath[int]) -> int:
        return item_id

    @asgi("/mount", is_mount=True, middleware=[config.middleware])
    async def mount(scope: Scope, receive: Receive, send: Send) -> None:
        await ASGIResponse(body=b"")(scope, receive, send)

    router = Router("/router", route_handlers=[router_handler], middleware=[config.middleware])
    with create_test_client([handler, mount, router]) as client:
        assert client.get("/articles/9041").status_code == 200
        assert client.get("/router/items/1").status_code == 200
        # The path left to the mount also matches a route of the app.
        assert client.get("/mount/articles/9041").status_code == 200

    server_spans = [span for span in exporter.get_finished_spans() if span.kind == SpanKind.SERVER]
    assert [span.name for span in server_spans] == [
        "GET /articles/{article_id}",
        "GET /router/items/{item_id}",
        "GET /mount",
    ]


def test_middleware_wrapping_litestar_app(config: OpenTelemetryConfig, exporter: InMemorySpanExporter) -> None:
    @get("/")
    async def handler() -> str:
        return "hello"

    app = config.middleware_class(app=Litestar([handler]), config=config)
    with TestClient(app) as client:
        assert client.get("/").text == "hello"

    server_span = next(span for span in exporter.get_finished_spans() if span.kind == SpanKind.SERVER)
    assert server_span.name == "GET"


async def test_unmatched_websocket_route(app_config: AppConfig, exporter: InMemorySpanExporter, scope: Scope) -> None:
    app = Litestar([], middleware=app_config.middleware, plugins=app_config.plugins)
    scope_dict = cast("dict[str, Any]", scope)
    scope_dict["type"] = "websocket"
    scope_dict.pop("method")
    await app(scope, AsyncMock(return_value={"type": "websocket.connect"}), AsyncMock())

    server_span = next(span for span in exporter.get_finished_spans() if span.kind == SpanKind.SERVER)
    assert server_span.name == "websocket"
    assert server_span.attributes is not None
    assert "http.route" not in server_span.attributes


def test_http_metrics_use_route_templates(
    app_config: AppConfig, reader: InMemoryMetricReader, request: FixtureRequest, mocker: MockerFixture
) -> None:
    from opentelemetry.instrumentation._semconv import _StabilityMode

    # Include stable HTTP metrics.
    mocker.patch(
        "opentelemetry.instrumentation.asgi._OpenTelemetrySemanticConventionStability."
        "_get_opentelemetry_stability_opt_in_mode",
        return_value=_StabilityMode.HTTP_DUP,
    )

    @get("/articles/{article_id:int}")
    async def handler(article_id: FromPath[int]) -> int:
        return article_id

    with create_test_client(handler, middleware=app_config.middleware, plugins=app_config.plugins) as client:
        assert client.get("/articles/9041").status_code == 200
        assert client.get("/articles/9042").status_code == 200
        assert client.get("/missing").status_code == 404

    metrics_data = reader.get_metrics_data()
    assert metrics_data is not None
    scope_metrics = next(
        sm
        for rm in metrics_data.resource_metrics
        for sm in rm.scope_metrics
        if sm.scope.name == f"litestar-test-{request.node.nodeid}"
    )
    metric = next(metric for metric in scope_metrics.metrics if metric.name == "http.server.request.duration")
    assert isinstance(metric.data, Histogram)
    routes = {
        cast("str | None", point.attributes.get("http.route")) for point in metric.data.data_points if point.attributes
    }
    assert routes == {"/articles/{article_id}", None}


@pytest.mark.parametrize(
    "child_path, child_template", [("/articles/9041", "/articles/{article_id}"), ("/missing", "/mount")]
)
def test_mounted_litestar_app(
    config: OpenTelemetryConfig, app_config: AppConfig, child_path: str, child_template: str
) -> None:
    templates: list[tuple[Litestar, str]] = []

    def request_hook(span: Span, scope: dict[str, Any]) -> None:
        templates.append((scope["litestar_app"], scope["path_template"]))

    config.server_request_hook_handler = request_hook

    @get("/articles/{article_id:int}")
    async def handler(article_id: FromPath[int]) -> int:
        return article_id

    child_app = Litestar([handler], plugins=[OpenTelemetryPlugin(config)])

    @asgi("/mount", is_mount=True)
    async def mount(scope: Scope, receive: Receive, send: Send) -> None:
        await child_app(scope, receive, send)

    with create_test_client(mount, middleware=app_config.middleware, plugins=app_config.plugins) as client:
        client.get(f"/mount{child_path}")

    assert templates == [(client.app, "/mount"), (child_app, child_template)]
