from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils.deprecation import warn_deprecation

__all__ = (
    "MiniJinjaTemplateEngine",
    "StateProtocol",
)

_FORWARDED = (*__all__, "MiniJinjaTemplate", "_transform_state")


def __getattr__(attr_name: str) -> object:
    from litestar.plugins import minijinja

    if attr_name in _FORWARDED:
        warn_deprecation(
            deprecated_name=f"litestar.contrib.minijinja.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            info=f"importing {attr_name} from 'litestar.contrib.minijinja' is deprecated, please "
            f"import it from 'litestar.plugins.minijinja' instead",
        )
        return getattr(minijinja, attr_name)

    if attr_name == "minijinja_from_state":
        warn_deprecation(
            "2.3.0",
            "minijinja_from_state",
            "import",
            removal_in="3.0.0",
            alternative="Use a callable that receives the minijinja State object as first argument.",
        )
        return minijinja._minijinja_from_state

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from litestar.plugins.minijinja import MiniJinjaTemplateEngine, StateProtocol
