# ruff: noqa: TCH004, F401
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("PrometheusController",)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar.plugins.prometheus import PrometheusController

        warn_deprecation(
            deprecated_name=f"litestar.contrib.prometheus.controller.{attr_name}",
            version="2.12.1",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.prometheus.controller' is deprecated, please "
            f"import it from 'litestar.plugins.prometheus' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from litestar.plugins.prometheus import PrometheusController
