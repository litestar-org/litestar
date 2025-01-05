# ruff: noqa: TC004, F401
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.utils import warn_deprecation

__all__ = ("AttrsSchemaPlugin", "is_attrs_class")


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar.plugins.attrs import AttrsSchemaPlugin, is_attrs_class

        warn_deprecation(
            deprecated_name=f"litestar.contrib.attrs.{attr_name}",
            version="2.13.0",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.attrs' is deprecated, please "
            f"import it from 'litestar.plugins.attrs' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from litestar.plugins.attrs import AttrsSchemaPlugin, is_attrs_class
