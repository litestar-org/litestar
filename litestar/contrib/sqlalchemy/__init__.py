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
            from advanced_alchemy.extensions.litestar import (
                repository,  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
            )

            value = globals()[attr_name] = getattr(repository, attr_name)
        elif attr_name == "wrap_sqlalchemy_exception":
            module = "litestar.plugins.sqlalchemy.exceptions"
            from advanced_alchemy.extensions.litestar import (
                exceptions,  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
            )

            value = globals()[attr_name] = getattr(exceptions, attr_name)

        else:  # pragma: no cover
            raise RuntimeError(f"Unhandled module attribute: {attr_name!r}")

        warn_deprecation(
            deprecated_name=f"litestar.contrib.sqlalchemy.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.sqlalchemy' is deprecated, please "
            f"import it from '{module}' instead",
        )

        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")  # pragma: no cover


if TYPE_CHECKING:
    from advanced_alchemy.exceptions import (  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
        wrap_sqlalchemy_exception,
    )
    from advanced_alchemy.repository import (  # type: ignore[import-not-found] # pyright: ignore[reportMissingImports]
        ModelT,
        SQLAlchemyAsyncRepository,
        SQLAlchemySyncRepository,
    )
