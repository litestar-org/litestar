# ruff: noqa: F401
from __future__ import annotations

from typing import TYPE_CHECKING  # pragma: no cover

from litestar.utils import warn_deprecation  # pragma: no cover

__all__ = ("PydanticSchemaPlugin",)  # pragma: no cover


def __getattr__(attr_name: str) -> object:  # pragma: no cover
    if attr_name in __all__:
        from litestar.plugins.pydantic.plugins.schema import PydanticSchemaPlugin

        warn_deprecation(
            deprecated_name=f"litestar.contrib.pydantic.pydantic_schema_plugin.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.pydantic.pydantic_schema_plugin' is deprecated, please "
            f"import it from 'litestar.plugins.pydantic' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from litestar.plugins.pydantic.plugins.schema import PydanticSchemaPlugin
