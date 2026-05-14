# ruff: noqa: F401
from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("OpenTelemetryConfig",)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar.plugins.opentelemetry import OpenTelemetryConfig

        warn_deprecation(
            deprecated_name=f"litestar.contrib.opentelemetry.config.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            info=f"importing {attr_name} from 'litestar.contrib.opentelemetry.config' is deprecated, please "
            f"import it from 'litestar.plugins.opentelemetry' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from litestar.plugins.opentelemetry import OpenTelemetryConfig
