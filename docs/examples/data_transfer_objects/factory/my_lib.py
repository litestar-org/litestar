from __future__ import annotations

from typing import Any

from sqlalchemy.orm import DeclarativeBase

from litestar.contrib.sqlalchemy.base import CommonTableAttributes, UUIDPrimaryKey, create_registry


class _Base(CommonTableAttributes, UUIDPrimaryKey, DeclarativeBase):
    """Fake base SQLAlchemy model for typing purposes."""


Base: _Base


def __getattr__(name: str) -> Any:
    if name == "Base":
        return type("Base", (CommonTableAttributes, UUIDPrimaryKey, DeclarativeBase), {"registry": create_registry()})
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
