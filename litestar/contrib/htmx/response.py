from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

if TYPE_CHECKING:
    from litestar_htmx import (  # noqa: TC004
        ClientRedirect,
        ClientRefresh,
        HTMXTemplate,
        HXLocation,
        HXStopPolling,
        PushUrl,
        ReplaceUrl,
        Reswap,
        Retarget,
        TriggerEvent,
    )

__all__ = (
    "ClientRedirect",
    "ClientRefresh",
    "HTMXTemplate",
    "HXLocation",
    "HXStopPolling",
    "PushUrl",
    "ReplaceUrl",
    "Reswap",
    "Retarget",
    "TriggerEvent",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        import litestar_htmx

        module = "litestar.plugins.htmx"
        value = globals()[attr_name] = getattr(litestar_htmx, attr_name)

        warn_deprecation(
            deprecated_name=f"litestar.contrib.htmx.response.{attr_name}",
            version="2.13",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.htmx.response' is deprecated, please import it from '{module}' instead",
        )

        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
