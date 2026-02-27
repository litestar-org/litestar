from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

warn_deprecation(
    deprecated_name="litestar.contrib.opentelemetry",
    version="2.18.0",
    kind="import",
    removal_in="3.0.0",
    info="The 'litestar.contrib.opentelemetry' module is deprecated. "
    "Please import from 'litestar.plugins.opentelemetry' instead.",
)

__all__ = (
    "OpenTelemetryConfig",
    "OpenTelemetryInstrumentationMiddleware",
    "OpenTelemetryPlugin",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar.plugins import opentelemetry

        value = globals()[attr_name] = getattr(opentelemetry, attr_name)
        warn_deprecation(
            deprecated_name=f"litestar.contrib.opentelemetry.{attr_name}",
            version="2.18.0",
            kind="import",
            removal_in="3.0.0",
            info=f"importing {attr_name} from 'litestar.contrib.opentelemetry' is deprecated, "
            f"import from 'litestar.plugins.opentelemetry' instead",
        )
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from litestar.plugins.opentelemetry import (
        OpenTelemetryConfig,
        OpenTelemetryInstrumentationMiddleware,
        OpenTelemetryPlugin,
    )
