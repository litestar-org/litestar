# ruff: noqa: TC004, F401
# pyright: reportUnusedImport=false
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "ModelT",
    "SQLAlchemyAsyncRepository",
    "SQLAlchemySyncRepository",
    "wrap_sqlalchemy_exception",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        if attr_name in ("SQLAlchemyAsyncRepository", "SQLAlchemySyncRepository", "ModelT"):
            module = "litestar.plugins.sqlalchemy.repository"
            from advanced_alchemy.repository import (  # type: ignore[import-not-found] # pyright: ignore[reportMissingImport]
                ModelT,
                SQLAlchemyAsyncRepository,
                SQLAlchemySyncRepository,
            )

        elif attr_name == "wrap_sqlalchemy_exception":
            module = "litestar.plugins.sqlalchemy.exceptions"
            from advanced_alchemy.exceptions import (  # type: ignore[import-not-found] # pyright: ignore[reportMissingImport]
                wrap_sqlalchemy_exception,  # type: ignore[import-not-found] # pyright: ignore[reportMissingImport]
            )

        else:  # pragma: no cover
            raise RuntimeError(f"Unhandled module attribute: {attr_name!r}")

        value = globals()[attr_name] = locals()[attr_name]
        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.repository.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy.repository' is deprecated, please "
            f"import it from '{module}' instead",
        )
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.exceptions import (  # type: ignore[import-not-found] # pyright: ignore[reportMissingImport]
        wrap_sqlalchemy_exception,
    )
    from advanced_alchemy.repository import (  # type: ignore[import-not-found] # pyright: ignore[reportMissingImport]
        ModelT,
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
    )
