"""Deprecated module — use :mod:`litestar.plugins.minijinja` instead.

This module re-exports the public surface of
:mod:`litestar.plugins.minijinja` (:class:`~litestar.plugins.minijinja.MiniJinjaTemplateEngine`,
:class:`~litestar.plugins.minijinja.StateProtocol`,
:class:`~litestar.plugins.minijinja.MiniJinjaTemplate`) and additionally
forwards the private helper ``_transform_state``, since
``litestar.plugins.flash`` historically imported it from this module via
a lazy import path. The shim emits a :class:`DeprecationWarning` on
attribute access; bare ``import litestar.contrib.minijinja`` is
intentionally silent so test collectors and similar tooling do not
trigger spurious warnings. The shim will be removed in Litestar 3.0.0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar.plugins.minijinja import (
        MiniJinjaTemplate,
        MiniJinjaTemplateEngine,
        StateProtocol,
        _transform_state,
    )

# Public symbols re-exported via the deprecation shim. Names listed here
# include the private ``_transform_state`` helper because external callers
# (most notably ``litestar.plugins.flash``) used to depend on its old
# import path; keeping it accessible avoids an unintentional break.
__all__ = (
    "MiniJinjaTemplate",
    "MiniJinjaTemplateEngine",
    "StateProtocol",
    "_transform_state",
)


def __getattr__(name: str) -> Any:
    if name in __all__:
        from litestar.plugins import minijinja as _new
        from litestar.utils.deprecation import warn_deprecation

        warn_deprecation(
            version="3.0.0b0",
            deprecated_name=f"litestar.contrib.minijinja.{name}",
            kind="import",
            removal_in="3.0.0",
            alternative=f"litestar.plugins.minijinja.{name}",
        )
        return getattr(_new, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
