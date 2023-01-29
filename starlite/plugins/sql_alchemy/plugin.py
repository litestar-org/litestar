from starlite.utils.deprecation import warn_deprecation

from ..sqlalchemy.plugin import SQLAlchemyPlugin

__all__ = ("SQLAlchemyPlugin",)

warn_deprecation(
    version="v1.51.0",
    deprecated_name="starlite.plugins.sql_alchemy.plugin",
    removal_in="v2.0.0",
    alternative="starlite.plugins.sqlalchemy.plugin",
    kind="import",
)
