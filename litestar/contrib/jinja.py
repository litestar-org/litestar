from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("JinjaTemplateEngine",)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar.plugins import jinja

        warn_deprecation(
            deprecated_name=f"litestar.contrib.jinja.{attr_name}",
            version="2.22.0",
            kind="import",
            removal_in="3.0.0",
            info=f"importing {attr_name} from 'litestar.contrib.jinja' is deprecated, please "
            f"import it from 'litestar.plugins.jinja' instead",
        )
        return getattr(jinja, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from litestar.plugins.jinja import JinjaTemplateEngine
