from starlite.utils.deprecation import warn_deprecation

from ..sqlalchemy.types import (
    SessionMakerInstanceProtocol,
    SessionMakerTypeProtocol,
    SQLAlchemyBinaryType,
)

__all__ = (
    "SQLAlchemyBinaryType",
    "SessionMakerInstanceProtocol",
    "SessionMakerTypeProtocol",
)

warn_deprecation(
    version="v1.51.0",
    deprecated_name="starlite.plugins.sql_alchemy.types",
    removal_in="v2.0.0",
    alternative="starlite.plugins.sqlalchemy.types",
    kind="import",
)
