from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

if TYPE_CHECKING:
    from litestar_htmx._utils import (  # noqa: TC004
        HTMXHeaders,
        get_headers,
        get_location_headers,
        get_push_url_header,
        get_redirect_header,
        get_refresh_header,
        get_replace_url_header,
        get_reswap_header,
        get_retarget_header,
        get_trigger_event_headers,
    )
__all__ = (
    "HTMXHeaders",
    "get_headers",
    "get_location_headers",
    "get_push_url_header",
    "get_redirect_header",
    "get_refresh_header",
    "get_replace_url_header",
    "get_reswap_header",
    "get_retarget_header",
    "get_trigger_event_headers",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar_htmx import _utils as utils

        module = "litestar.plugins.htmx._utils"
        value = globals()[attr_name] = getattr(utils, attr_name)

        warn_deprecation(
            deprecated_name=f"litestar.contrib.htmx._utils.{attr_name}",
            version="2.13",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.htmx._utils' is deprecated, please import it from '{module}' instead",
        )

        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
