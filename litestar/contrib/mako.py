"""Deprecated module — use :mod:`litestar.plugins.mako` instead.

This module re-exports :class:`~litestar.plugins.mako.MakoTemplateEngine`
and :class:`~litestar.plugins.mako.MakoTemplate` from their new home at
``litestar.plugins.mako`` and emits a :class:`DeprecationWarning` on
attribute access. The shim will be removed in Litestar 3.0.0; bare
``import litestar.contrib.mako`` is intentionally silent so that
downstream tooling (such as test collectors) does not trigger spurious
warnings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar.plugins.mako import MakoTemplate, MakoTemplateEngine

__all__ = ("MakoTemplate", "MakoTemplateEngine")


def __getattr__(name: str) -> Any:
    if name in __all__:
        from litestar.plugins import mako as _new
        from litestar.utils.deprecation import warn_deprecation

        warn_deprecation(
            version="3.0.0b0",
            deprecated_name=f"litestar.contrib.mako.{name}",
            kind="import",
            removal_in="3.0.0",
            alternative=f"litestar.plugins.mako.{name}",
        )
        return getattr(_new, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
