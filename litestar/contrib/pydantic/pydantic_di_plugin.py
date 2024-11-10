# ruff: noqa: TCH004, F401
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = ("PydanticDIPlugin",)


def __getattr__(attr_name: str) -> object:  # pragma: no cover
    if attr_name in __all__:
        from litestar.plugins.pydantic.plugins.di import PydanticDIPlugin

        warn_deprecation(
            deprecated_name=f"litestar.contrib.pydantic.pydantic_di_plugin.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.pydantic.pydantic_di_plugin' is deprecated, please "
            f"import it from 'litestar.plugins.pydantic' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from litestar.plugins.pydantic.plugins.di import PydanticDIPlugin
