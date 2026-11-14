from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar.exceptions import MissingDependencyException
from litestar.plugins.prometheus.middleware import (
    PrometheusMiddleware,
)
from litestar.utils.deprecation import warn_deprecation

__all__ = ("PrometheusConfig",)


try:
    import prometheus_client  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("prometheus_client", "prometheus-client", "prometheus") from e


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from litestar.connection.request import Request
    from litestar.types import Method, Scopes


@dataclass
class PrometheusConfig:
    """Configuration class for the PrometheusConfig middleware."""

    app_name: str = field(default="litestar")
    """The name of the application to use in the metrics."""
    prefix: str = "litestar"
    """The prefix to use for the metrics."""
    labels: Mapping[str, str | Callable] | None = field(default=None)
    """A mapping of labels to add to the metrics. The values can be either a string or a callable that returns a string."""
    exemplars: Callable[[Request], dict] | None = field(default=None)
    """A callable that returns a list of exemplars to add to the metrics. Only supported in opementrics-text exposition format."""
    buckets: Sequence[str | float] | None = field(default=None)
    """A list of buckets to use for the histogram."""
    excluded_http_methods: Method | Sequence[Method] | None = field(default=None)
    """A list of http methods to exclude from the metrics."""
    exclude_unhandled_paths: bool = field(default=False)
    """Whether to ignore requests for unhandled paths from the metrics."""
    exclude: str | list[str] | None = field(default=None)
    """A pattern or list of patterns for routes to exclude from the metrics."""
    exclude_opt_key: str | None = field(default=None)
    """A key or list of keys in ``opt`` with which a route handler can "opt-out" of the middleware."""
    scopes: Scopes | None = field(default=None)
    """ASGI scopes processed by the middleware, if None both ``http`` and ``websocket`` will be processed."""
    middleware_class: type[PrometheusMiddleware] = field(default=PrometheusMiddleware)
    """The middleware class to use.
    """
    group_path: bool = field(default=True)
    """Whether to group paths in the metrics to avoid cardinality explosion.
    """

    @property
    def middleware(self) -> PrometheusMiddleware:
        """Create an instance of :class:`PrometheusMiddleware <litestar.plugins.prometheus.PrometheusMiddleware>`,
        or a subclass of this middleware, configured from this config instance.

        Returns:
            An instance of :attr:`middleware_class`.
        """
        warn_deprecation(
            version="3.0",
            deprecated_name="PrometheusConfig.middleware",
            kind="property",
            removal_in="4.0",
            alternative="PrometheusMiddleware",
            info="Construct a PrometheusMiddleware instance directly and pass it to the middleware list",
        )
        return self.middleware_class(
            app_name=self.app_name,
            prefix=self.prefix,
            labels=self.labels,
            exemplars=self.exemplars,
            buckets=self.buckets,
            excluded_http_methods=self.excluded_http_methods,
            exclude=self.exclude,
            exclude_opt_key=self.exclude_opt_key,
            scopes=self.scopes,
            group_path=self.group_path,
        )
