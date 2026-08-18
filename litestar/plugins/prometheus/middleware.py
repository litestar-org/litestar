from __future__ import annotations

import time
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar, cast

from litestar.connection.request import Request
from litestar.enums import ScopeType
from litestar.exceptions import HTTPException, MissingDependencyException
from litestar.middleware.base import ASGIMiddleware

__all__ = ("PrometheusMiddleware",)

from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

try:
    import prometheus_client  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("prometheus_client", "prometheus-client", "prometheus") from e

from prometheus_client import Counter, Gauge, Histogram

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from prometheus_client.metrics import MetricWrapperBase

    from litestar.types import ASGIApp, Message, Method, Receive, Scope, Scopes, Send


class PrometheusMiddleware(ASGIMiddleware):
    """Prometheus Middleware."""

    _metrics: ClassVar[dict[str, MetricWrapperBase]] = {}

    def __init__(
        self,
        *,
        app_name: str = "litestar",
        prefix: str = "litestar",
        labels: Mapping[str, str | Callable] | None = None,
        exemplars: Callable[[Request], dict] | None = None,
        buckets: Sequence[str | float] | None = None,
        excluded_http_methods: Method | Sequence[Method] | None = None,
        exclude: str | list[str] | None = None,
        exclude_opt_key: str | None = None,
        scopes: Scopes | None = None,
        group_path: bool = True,
    ) -> None:
        """Middleware that adds Prometheus instrumentation to the application.

        Args:
            app_name: The name of the application to use in the metrics.
            prefix: The prefix to use for the metrics.
            labels: A mapping of labels to add to the metrics. The values can be either a string or a callable that
                returns a string.
            exemplars: A callable that returns a list of exemplars to add to the metrics. Only supported in
                openmetrics-text exposition format.
            buckets: A list of buckets to use for the histogram.
            excluded_http_methods: A list of http methods to exclude from the metrics.
            exclude: A pattern or list of patterns for routes to exclude from the metrics, matched against the
                handler path.
            exclude_opt_key: A key in ``opt`` with which a route handler can "opt-out" of the middleware.
            scopes: ASGI scopes processed by the middleware; if ``None`` or empty, ``http``, ``websocket`` and ASGI
                route handlers are all processed. Mounted ASGI apps stay wrapped regardless, with their connections
                filtered by scope type.
            group_path: Whether to group paths in the metrics to avoid cardinality explosion.
        """
        self.app_name = app_name
        self.prefix = prefix
        self.labels = labels
        self.exemplars = exemplars
        self.excluded_http_methods = excluded_http_methods
        self.exclude_path_pattern = tuple(exclude) if isinstance(exclude, list) else exclude
        self.exclude_opt_key = exclude_opt_key
        self.group_path = group_path
        if scopes:
            scope_types = frozenset(scopes)
            self.scopes = (*(s for s in (ScopeType.HTTP, ScopeType.WEBSOCKET) if s in scope_types), ScopeType.ASGI)
            self.should_bypass_for_scope = lambda scope: scope["type"] not in scope_types

        self._kwargs: dict[str, Any] = {}
        if buckets is not None:
            self._kwargs["buckets"] = buckets

    def request_count(self, labels: dict[str, str | int | float]) -> Counter:
        metric_name = f"{self.prefix}_requests_total"

        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Counter(
                name=metric_name,
                documentation="Total requests",
                labelnames=[*labels.keys()],
            )

        return cast("Counter", PrometheusMiddleware._metrics[metric_name])

    def request_time(self, labels: dict[str, str | int | float]) -> Histogram:
        metric_name = f"{self.prefix}_request_duration_seconds"

        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Histogram(
                name=metric_name,
                documentation="Request duration, in seconds",
                labelnames=[*labels.keys()],
                **self._kwargs,
            )
        return cast("Histogram", PrometheusMiddleware._metrics[metric_name])

    def requests_in_progress(self, labels: dict[str, str | int | float]) -> Gauge:
        metric_name = f"{self.prefix}_requests_in_progress"

        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Gauge(
                name=metric_name,
                documentation="Total requests currently in progress",
                labelnames=[*labels.keys()],
                multiprocess_mode="livesum",
            )
        return cast("Gauge", PrometheusMiddleware._metrics[metric_name])

    def requests_error_count(self, labels: dict[str, str | int | float]) -> Counter:
        metric_name = f"{self.prefix}_requests_error_total"

        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Counter(
                name=metric_name,
                documentation="Total errors in requests",
                labelnames=[*labels.keys()],
            )
        return cast("Counter", PrometheusMiddleware._metrics[metric_name])

    def _get_extra_labels(self, request: Request[Any, Any, Any]) -> dict[str, str]:
        """Get extra labels provided by the config and if they are callable, parse them.

        Args:
        request: The request object.

        Returns:
        A dictionary of extra labels.
        """

        return {k: str(v(request) if callable(v) else v) for k, v in (self.labels or {}).items()}

    def _get_default_labels(self, request: Request[Any, Any, Any]) -> dict[str, str | int | float]:
        """Get default label values from the request.

        Args:
            request: The request object.

        Returns:
            A dictionary of default labels.
        """

        path = request.url.path
        if self.group_path:
            path = request.scope["path_template"]
        return {
            "method": request.method if request.scope["type"] == ScopeType.HTTP else request.scope["type"],
            "path": path,
            "status_code": 200,
            "app_name": self.app_name,
        }

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Handle ASGI call.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
            next_app: The next ASGI application in the middleware stack to call.

        Returns:
            None
        """

        request = Request[Any, Any, Any](scope, receive)

        if self.excluded_http_methods and request.method in self.excluded_http_methods:
            await next_app(scope, receive, send)
            return

        labels = {**self._get_default_labels(request), **self._get_extra_labels(request)}

        request_span = {"start_time": time.perf_counter(), "end_time": 0, "duration": 0, "status_code": 200}

        wrapped_send = self._get_wrapped_send(send, request_span)

        self.requests_in_progress(labels).labels(*labels.values()).inc()

        try:
            try:
                await next_app(scope, receive, wrapped_send)
            except HTTPException as exc:
                request_span["status_code"] = exc.status_code
                raise
            except Exception:
                request_span["status_code"] = HTTP_500_INTERNAL_SERVER_ERROR
                raise
        finally:
            extra: dict[str, Any] = {}
            if self.exemplars:
                extra["exemplar"] = self.exemplars(request)

            self.requests_in_progress(labels).labels(*labels.values()).dec()

            labels["status_code"] = request_span["status_code"]
            label_values = [*labels.values()]

            if request_span["status_code"] >= HTTP_500_INTERNAL_SERVER_ERROR:
                self.requests_error_count(labels).labels(*label_values).inc(**extra)

            self.request_count(labels).labels(*label_values).inc(**extra)
            self.request_time(labels).labels(*label_values).observe(request_span["duration"], **extra)

    def _get_wrapped_send(self, send: Send, request_span: dict[str, float]) -> Callable:
        @wraps(send)
        async def wrapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                request_span["status_code"] = message["status"]

            if message["type"] == "http.response.body":
                end = time.perf_counter()
                request_span["duration"] = end - request_span["start_time"]
                request_span["end_time"] = end
            await send(message)

        return wrapped_send
