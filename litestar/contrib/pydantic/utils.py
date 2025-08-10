# ruff: noqa: F401
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.utils import warn_deprecation

__all__ = (
    "get_model_info",
    "is_pydantic_constrained_field",
    "is_pydantic_model_class",
    "is_pydantic_undefined",
    "is_pydantic_v2",
)


def __getattr__(attr_name: str) -> object:
    if attr_name in __all__:
        from litestar.plugins.pydantic.utils import (
            get_model_info,
            is_pydantic_constrained_field,
            is_pydantic_model_class,
            is_pydantic_undefined,
            is_pydantic_v2,
        )

        warn_deprecation(
            deprecated_name=f"litestar.contrib.pydantic.utils.{attr_name}",
            version="2.12",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.pydantic.utils' is deprecated, please "
            f"import it from 'litestar.plugins.pydantic.utils' instead",
        )
        value = globals()[attr_name] = locals()[attr_name]
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")


if TYPE_CHECKING:
    from litestar.plugins.pydantic.utils import (
        get_model_info,
        is_pydantic_constrained_field,
        is_pydantic_model_class,
        is_pydantic_undefined,
        is_pydantic_v2,
    )
