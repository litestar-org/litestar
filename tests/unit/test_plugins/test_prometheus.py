import re
import time
from pathlib import Path
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from prometheus_client import REGISTRY
from pytest_mock import MockerFixture

from litestar import get, post, websocket_listener
from litestar.exceptions import HTTPException, NotAuthorizedException, PermissionDeniedException
from litestar.params import FromPath
from litestar.plugins.prometheus import PrometheusConfig, PrometheusController, PrometheusMiddleware
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


def create_middleware(**kwargs: Any) -> PrometheusMiddleware:
    _reset_registry()
    return PrometheusMiddleware(**kwargs)


def _reset_registry() -> None:
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)

    PrometheusMiddleware._metrics = {}


@pytest.mark.flaky(reruns=5)
def test_prometheus_exporter_metrics_with_http() -> None:
    prometheus_middleware = create_middleware()

    @get("/duration")
    def duration_handler() -> dict:
        time.sleep(0.1)
        return {"hello": "world"}

    @get("/error")
    def handler_error() -> dict:
        raise HTTPException("Error Occurred", status_code=500)

    with create_test_client(
        [duration_handler, handler_error, PrometheusController], middleware=[prometheus_middleware]
    ) as client:
        client.get("/error")
        client.get("/duration")
        metrics_exporter_response = client.get("/metrics")

        assert metrics_exporter_response.status_code == HTTP_200_OK
        metrics = metrics_exporter_response.content.decode()

        assert (
            """litestar_request_duration_seconds_sum{app_name="litestar",method="GET",path="/duration",status_code="200"}"""
            in metrics
        )

        assert (
            """litestar_requests_error_total{app_name="litestar",method="GET",path="/error",status_code="500"} 1.0"""
            in metrics
        )

        assert (
            """litestar_request_duration_seconds_bucket{app_name="litestar",le="0.005",method="GET",path="/error",status_code="500"} 1.0"""
            in metrics
        )

        assert (
            """litestar_requests_in_progress{app_name="litestar",method="GET",path="/metrics",status_code="200"} 1.0"""
            in metrics
        )

        assert (
            """litestar_requests_in_progress{app_name="litestar",method="GET",path="/duration",status_code="200"} 0.0"""
            in metrics
        )

        duration_metric_matches = re.findall(
            r"""litestar_request_duration_seconds_sum{app_name="litestar",method="GET",path="/duration",status_code="200"} (\d+\.\d+)""",
            metrics,
        )

        assert duration_metric_matches != []
        assert round(float(duration_metric_matches[0]), 1) == 0.1

        client.get("/duration")
        metrics = client.get("/metrics").content.decode()

        assert (
            """litestar_requests_total{app_name="litestar",method="GET",path="/duration",status_code="200"} 2.0"""
            in metrics
        )

        assert (
            """litestar_requests_in_progress{app_name="litestar",method="GET",path="/error",status_code="200"} 0.0"""
            in metrics
        )

        assert (
            """litestar_requests_in_progress{app_name="litestar",method="GET",path="/metrics",status_code="200"} 1.0"""
            in metrics
        )


def test_prometheus_group_path_defaults_to_true() -> None:
    assert PrometheusConfig().group_path is True


def test_prometheus_group_path_default_uses_route_template_for_parameterized_routes() -> None:
    prometheus_middleware = create_middleware()

    @get("/users/{user_id:int}")
    def get_user(user_id: FromPath[int]) -> dict:
        return {"user_id": user_id}

    with create_test_client([get_user, PrometheusController], middleware=[prometheus_middleware]) as client:
        for user_id in range(1, 4):
            client.get(f"/users/{user_id}")
        metrics = client.get("/metrics").content.decode()

        assert (
            """litestar_requests_total{app_name="litestar",method="GET",path="/users/{user_id}",status_code="200"} 3.0"""
            in metrics
        )
        assert 'path="/users/1"' not in metrics
        assert 'path="/users/2"' not in metrics
        assert 'path="/users/3"' not in metrics


def test_prometheus_middleware_configurations() -> None:
    labels = {"foo": "bar", "baz": lambda a: "qux"}

    prometheus_middleware = create_middleware(
        app_name="litestar_test",
        prefix="litestar_rocks",
        labels=labels,
        buckets=[0.1, 0.5, 1.0],
        excluded_http_methods=["POST"],
    )

    @get("/test")
    def test() -> dict:
        return {"hello": "world"}

    @post("/ignore")
    def ignore() -> dict:
        return {"hello": "world"}

    with create_test_client([test, ignore, PrometheusController], middleware=[prometheus_middleware]) as client:
        client.get("/test")
        client.post("/ignore")
        metrics_exporter_response = client.get("/metrics")

        assert metrics_exporter_response.status_code == HTTP_200_OK
        metrics = metrics_exporter_response.content.decode()

        assert (
            """litestar_rocks_requests_total{app_name="litestar_test",baz="qux",foo="bar",method="GET",path="/test",status_code="200"} 1.0"""
            in metrics
        )

        assert (
            """litestar_rocks_requests_total{app_name="litestar_test",baz="qux",foo="bar",method="POST",path="/ignore",status_code="201"} 1.0"""
            not in metrics
        )

        assert (
            """litestar_rocks_request_duration_seconds_bucket{app_name="litestar_test",baz="qux",foo="bar",le="0.1",method="GET",path="/test",status_code="200"} 1.0"""
            in metrics
        )

        assert (
            """litestar_rocks_request_duration_seconds_bucket{app_name="litestar_test",baz="qux",foo="bar",le="0.5",method="GET",path="/test",status_code="200"} 1.0"""
            in metrics
        )

        assert (
            """litestar_rocks_request_duration_seconds_bucket{app_name="litestar_test",baz="qux",foo="bar",le="1.0",method="GET",path="/test",status_code="200"} 1.0"""
            in metrics
        )

        # default-bucket boundaries must be absent, proving the custom buckets replaced them
        assert """le="0.005",method="GET",path="/test""" not in metrics


def test_prometheus_controller_configurations() -> None:
    prometheus_middleware = create_middleware(
        exemplars=lambda a: {"trace_id": "1234"},
    )

    class CustomPrometheusController(PrometheusController):
        path: str = "/metrics/custom"
        openmetrics_format: bool = True

    @get("/test")
    def test() -> dict:
        return {"hello": "world"}

    with create_test_client([test, CustomPrometheusController], middleware=[prometheus_middleware]) as client:
        client.get("/test")

        metrics_exporter_response = client.get("/metrics/custom")

        assert metrics_exporter_response.status_code == HTTP_200_OK
        metrics = metrics_exporter_response.content.decode()

        assert (
            """litestar_requests_total{app_name="litestar",method="GET",path="/test",status_code="200"} 1.0 # {trace_id="1234"} 1.0"""
            in metrics
        )


def test_prometheus_with_websocket() -> None:
    prometheus_middleware = create_middleware()

    @websocket_listener("/test")
    def test(data: str) -> dict:
        return {"hello": data}

    with create_test_client([test, PrometheusController], middleware=[prometheus_middleware]) as client:
        with client.websocket_connect("/test") as websocket:
            websocket.send_text("litestar")
            websocket.receive_json()

        metrics_exporter_response = client.get("/metrics")

        assert metrics_exporter_response.status_code == HTTP_200_OK
        metrics = metrics_exporter_response.content.decode()

        assert (
            """litestar_requests_total{app_name="litestar",method="websocket",path="/test",status_code="200"} 1.0"""
            in metrics
        )


@pytest.mark.parametrize("env_var", ["PROMETHEUS_MULTIPROC_DIR", "prometheus_multiproc_dir"])
def test_procdir(monkeypatch: MonkeyPatch, tmp_path: Path, mocker: MockerFixture, env_var: str) -> None:
    proc_dir = tmp_path / "something"
    proc_dir.mkdir()
    monkeypatch.setenv(env_var, str(proc_dir))
    prometheus_middleware = create_middleware()
    mock_registry = mocker.patch("litestar.plugins.prometheus.controller.CollectorRegistry")
    mock_collector = mocker.patch("litestar.plugins.prometheus.controller.multiprocess.MultiProcessCollector")

    with create_test_client([PrometheusController], middleware=[prometheus_middleware]) as client:
        client.get("/metrics")

    mock_collector.assert_called_once_with(mock_registry.return_value)


def test_prometheus_middleware_records_correct_status_for_auth_exceptions() -> None:
    """Test that PrometheusMiddleware correctly records HTTP exception status codes.

    This test verifies the fix for the issue where NotAuthorizedException and other
    HTTP exceptions were being recorded with status_code=200 instead of their actual
    status codes (e.g., 401, 403).
    """
    prometheus_middleware = create_middleware()

    @get("/protected")
    def protected_handler() -> dict:
        raise NotAuthorizedException("Invalid token")

    @get("/forbidden")
    def forbidden_handler() -> dict:
        raise PermissionDeniedException("Access denied")

    @get("/server_error")
    def server_error_handler() -> dict:
        raise HTTPException("Server error", status_code=500)

    with create_test_client(
        [protected_handler, forbidden_handler, server_error_handler, PrometheusController],
        middleware=[prometheus_middleware],
    ) as client:
        # Test 401 Unauthorized
        response = client.get("/protected")
        assert response.status_code == 401

        # Test 403 Forbidden
        response = client.get("/forbidden")
        assert response.status_code == 403

        # Test 500 Server Error
        response = client.get("/server_error")
        assert response.status_code == 500

        # Check metrics
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == HTTP_200_OK
        metrics = metrics_response.content.decode()

        # Verify 401 is recorded correctly
        assert (
            """litestar_requests_total{app_name="litestar",method="GET",path="/protected",status_code="401"} 1.0"""
            in metrics
        )

        # Verify 403 is recorded correctly
        assert (
            """litestar_requests_total{app_name="litestar",method="GET",path="/forbidden",status_code="403"} 1.0"""
            in metrics
        )

        # Verify 500 is recorded correctly
        assert (
            """litestar_requests_total{app_name="litestar",method="GET",path="/server_error",status_code="500"} 1.0"""
            in metrics
        )

        # Verify error count is incremented for 5xx errors
        assert (
            """litestar_requests_error_total{app_name="litestar",method="GET",path="/server_error",status_code="500"} 1.0"""
            in metrics
        )


def test_prometheus_middleware_records_generic_exception_as_500() -> None:
    """Test that PrometheusMiddleware records generic exceptions as 500.

    This test verifies that non-HTTPException errors are recorded with status_code=500
    in Prometheus metrics.
    """
    prometheus_middleware = create_middleware()

    @get("/generic_error")
    def generic_error_handler() -> dict:
        raise ValueError("Something went wrong")

    with create_test_client(
        [generic_error_handler, PrometheusController],
        middleware=[prometheus_middleware],
    ) as client:
        # Test generic exception
        response = client.get("/generic_error")
        # The exception is caught by Litestar's exception handler and converted to 500
        assert response.status_code == 500

        # Check metrics
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == HTTP_200_OK
        metrics = metrics_response.content.decode()

        # Verify 500 is recorded correctly for generic exceptions
        assert (
            """litestar_requests_total{app_name="litestar",method="GET",path="/generic_error",status_code="500"} 1.0"""
            in metrics
        )

        # Verify error count is incremented
        assert (
            """litestar_requests_error_total{app_name="litestar",method="GET",path="/generic_error",status_code="500"} 1.0"""
            in metrics
        )


def test_prometheus_mounted_asgi_apps_are_instrumented() -> None:
    from litestar.handlers import ASGIRouteHandler
    from litestar.response.base import ASGIResponse

    prometheus_middleware = create_middleware(group_path=False)

    asgi_handler = ASGIRouteHandler("/mounted", is_mount=True, fn=ASGIResponse(body="something"))

    with create_test_client([asgi_handler, PrometheusController], middleware=[prometheus_middleware]) as client:
        client.get("/mounted")
        metrics = client.get("/metrics").content.decode()

        assert 'path="/"' in metrics


def test_prometheus_group_path_disabled_uses_request_path() -> None:
    prometheus_middleware = create_middleware(group_path=False)

    @get("/users/{user_id:int}")
    def get_user(user_id: FromPath[int]) -> dict:
        return {"user_id": user_id}

    with create_test_client([get_user, PrometheusController], middleware=[prometheus_middleware]) as client:
        client.get("/users/1")
        metrics = client.get("/metrics").content.decode()

        assert 'path="/users/1"' in metrics
        assert 'path="/users/{user_id}"' not in metrics


def test_prometheus_scopes_enforced_for_connections_through_mounts() -> None:
    from litestar.handlers import ASGIRouteHandler
    from litestar.response.base import ASGIResponse

    # mounted ASGI apps stay wrapped regardless of scopes, so restricting to websocket must
    # still exclude http connections through the mount at runtime
    prometheus_middleware = create_middleware(scopes={"websocket"}, group_path=False)

    asgi_handler = ASGIRouteHandler("/mounted", is_mount=True, fn=ASGIResponse(body="something"))

    with create_test_client([asgi_handler, PrometheusController], middleware=[prometheus_middleware]) as client:
        client.get("/mounted")
        metrics = client.get("/metrics").content.decode()

        assert 'path="/"' not in metrics


def test_prometheus_custom_middleware_subclass() -> None:
    class CustomPrometheusMiddleware(PrometheusMiddleware):
        async def handle(self, scope: Any, receive: Any, send: Any, next_app: Any) -> None:
            self.app_name = "overridden"
            await super().handle(scope, receive, send, next_app)

    _reset_registry()
    prometheus_middleware = CustomPrometheusMiddleware()

    @get("/test")
    def handler() -> dict:
        return {"hello": "world"}

    with create_test_client([handler, PrometheusController], middleware=[prometheus_middleware]) as client:
        client.get("/test")
        metrics = client.get("/metrics").content.decode()

        assert 'app_name="overridden"' in metrics


def test_config_middleware_property_deprecated() -> None:
    _reset_registry()
    config = PrometheusConfig(app_name="deprecated-path")

    with pytest.warns(DeprecationWarning, match="PrometheusConfig.middleware"):
        middleware = config.middleware

    assert isinstance(middleware, PrometheusMiddleware)
    assert middleware.app_name == "deprecated-path"
