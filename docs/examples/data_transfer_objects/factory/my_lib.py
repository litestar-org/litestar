from __future__ import annotations

from typing import Any

from advanced_alchemy.extensions.litestar import base, mixins
from sqlalchemy.orm import DeclarativeBase


class _Base(base.CommonTableAttributes, mixins.UUIDPrimaryKey, DeclarativeBase):
    """Fake base SQLAlchemy model for typing purposes."""


Base: _Base


def __getattr__(name: str) -> Any:
    if name == "Base":
        return type(
            "Base",
            (base.CommonTableAttributes, mixins.UUIDPrimaryKey, DeclarativeBase),
            {"registry": base.create_registry()},
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
