# ruff: noqa: F401
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "get_instrumented_attr",
    "wrap_sqlalchemy_exception",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from advanced_alchemy.exceptions import (
            wrap_sqlalchemy_exception,  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
        )
        from advanced_alchemy.repository import (
            get_instrumented_attr,  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
        )

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.repository._util.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.repository._util' is deprecated, please "
            f"import it from 'litestar.plugins.sqlalchemy.repository' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.exceptions import (
        wrap_sqlalchemy_exception,  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
    )
    from advanced_alchemy.repository import (
        get_instrumented_attr,  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
    )
