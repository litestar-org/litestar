from __future__ import annotations

import time
from collections import OrderedDict
from functools import wraps
from typing import TYPE_CHECKING, Callable

from litestar.connection.request import Request
from litestar.exceptions import MissingDependencyException
from litestar.middleware.base import AbstractMiddleware

__all__ = ("PrometheusMiddleware",)


try:
    import prometheus_client  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("prometheus_client") from e

from prometheus_client import Counter, Gauge, Histogram

if TYPE_CHECKING:
    from prometheus_client.metrics import MetricWrapperBase

    from litestar.contrib.prometheus import PrometheusConfig
    from litestar.types import ASGIApp, Message, Receive, Scope, Send


class PrometheusMiddleware(AbstractMiddleware):
    """Prometheus Middleware."""

    _metrics: dict[str, MetricWrapperBase] = {}

    def __init__(self, app: ASGIApp, config: PrometheusConfig):
        """Middleware that adds Prometheus instrumentation to the application.

        Args:
            app: The ``next`` ASGI app to call.
            config: An instance of :class:`PrometheusConfig <.contrib.prometheus.PrometheusConfig>`
        """
        super().__init__(app=app, scopes=config.scopes, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key)
        self._config = config
        self._labels = OrderedDict(self._config.labels) if self._config.labels is not None else None
        self._kwargs = {}

        if self._config.buckets is not None:
            self._kwargs["buckets"] = self._config.buckets

    def request_count(self, labels: dict[str, str | int | float]) -> Counter:
        metric_name = f"{self._config.prefix}_requests_total"
        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Counter(
                metric_name,
                "Total requests",
                [*labels.keys()],
            )
        return PrometheusMiddleware._metrics[metric_name]  # type: ignore

    def request_time(self, labels: dict[str, str | int | float]) -> Histogram:
        metric_name = f"{self._config.prefix}_request_duration_seconds"
        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Histogram(
                metric_name,
                "Request duration, in seconds",
                [*labels.keys()],
                **self._kwargs,  # type: ignore
            )
        return PrometheusMiddleware._metrics[metric_name]  # type: ignore

    def requests_in_progress(self, labels: dict[str, str | int | float]) -> Gauge:
        metric_name = f"{self._config.prefix}_requests_in_progress"
        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Gauge(
                metric_name,
                "Total requests currently in progress",
                [*labels.keys()],
                multiprocess_mode="livesum",
            )
        return PrometheusMiddleware._metrics[metric_name]  # type: ignore

    def requests_error_count(self, labels: dict[str, str | int | float]) -> Counter:
        metric_name = f"{self._config.prefix}_requests_error_total"
        if metric_name not in PrometheusMiddleware._metrics:
            PrometheusMiddleware._metrics[metric_name] = Counter(
                metric_name,
                "Total errors in requests",
                [*labels.keys()],
            )
        return PrometheusMiddleware._metrics[metric_name]  # type: ignore

    def _get_extra_labels(self, request: Request) -> dict[str, str | int | float]:
        """Get extra labels provided by the config and if they are callable, parse them."""

        extra_labels: dict[str, str | int | float] = {}
        if self._labels is None:
            return extra_labels

        for key, value in self._labels.items():
            if callable(value):
                parsed_value = ""
                try:
                    parsed_value = value(request)
                finally:
                    extra_labels[key] = str(parsed_value)
            else:
                extra_labels[key] = value

        return extra_labels

    def _get_default_labels(self, request: Request) -> dict[str, str | int | float]:
        """Get default label values from the request.

        Default:
            - method
            - path
            - status_code
            - app_name
        """

        return {
            "method": request.method,
            "path": request.url.path,
            "status_code": 200,
            "app_name": self._config.app_name,
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """

        request: Request = Request(scope, receive)
        method = request.method

        if self._config.exclude_http_methods and method in self._config.exclude_http_methods:
            await self.app(scope, receive, send)
            return

        labels = self._get_default_labels(request)
        extra_labels = self._get_extra_labels(request)
        labels.update(extra_labels)
        label_values = [*labels.values()]
        request_span = {"start_time": time.perf_counter(), "end_time": 0, "duration": 0, "status_code": 200}

        self.requests_in_progress(labels).labels(*label_values).inc()
        wrapped_send = self._get_wrapped_send(send, request_span)

        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            extra = {}
            if self._config.exemplars:
                extra["exemplar"] = self._config.exemplars(request)

            self.requests_in_progress(labels).labels(*label_values).dec()

            labels["status_code"] = request_span["status_code"]
            label_values = [*labels.values()]

            if request_span["status_code"] >= 500:
                self.requests_error_count(labels).labels(*label_values).inc(**extra)  # type: ignore

            self.request_count(labels).labels(*label_values).inc(**extra)  # type: ignore
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
