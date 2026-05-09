"""Deprecated module — use :mod:`litestar.plugins.jinja` instead.

This module re-exports :class:`~litestar.plugins.jinja.JinjaTemplateEngine`
from its new home at ``litestar.plugins.jinja`` and emits a
:class:`DeprecationWarning` on attribute access. The shim will be removed
in Litestar 3.0.0; bare ``import litestar.contrib.jinja`` is intentionally
silent so that downstream tooling (such as test collectors) does not
trigger spurious warnings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar.plugins.jinja import JinjaTemplateEngine

__all__ = ("JinjaTemplateEngine",)


def __getattr__(name: str) -> Any:
    if name in __all__:
        from litestar.plugins import jinja as _new
        from litestar.utils.deprecation import warn_deprecation

        warn_deprecation(
            version="3.0.0b0",
            deprecated_name=f"litestar.contrib.jinja.{name}",
            kind="import",
            removal_in="3.0.0",
            alternative=f"litestar.plugins.jinja.{name}",
        )
        return getattr(_new, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
