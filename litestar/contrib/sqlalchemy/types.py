from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON as _JSON
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect


class JSON(TypeDecorator):
    """Platform-independent JSON type.

    Uses JSONB type for postgres, otherwise uses the generic JSON data type.
    """

    class JSONType(String):
        python_type = dict[str, Any]

    impl = JSONType
    cache_ok = True

    def load_dialect_impl(self, dialect: "Dialect") -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())  # type: ignore[no-untyped-call]
        return dialect.type_descriptor(_JSON())

    @property
    def python_type(self) -> type[dict[str, Any]]:
        return self.impl.python_type
