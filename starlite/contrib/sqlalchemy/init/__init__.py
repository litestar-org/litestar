from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from starlite.di import Provide
from starlite.exceptions import MissingDependencyException

from .config import SQLAlchemyConfig

try:
    import sqlalchemy  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("sqlalchemy is not installed") from e

if TYPE_CHECKING:
    from starlite.config.app import AppConfig

__all__ = ("SQLAlchemyInit",)


class SQLAlchemyInit:
    """SQLAlchemy application lifecycle configuration."""

    __slots__ = ("_config",)

    def __init__(self, sqlalchemy_config: Optional["SQLAlchemyConfig"] = None) -> None:
        """Initialize ``SQLAlchemyPlugin``.

        Args:
            sqlalchemy_config: configure DB connection and hook handlers and dependencies.
        """
        self._config = sqlalchemy_config or SQLAlchemyConfig()

    def __call__(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with SQLAlchemy.

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """
        app_config.dependencies[self._config.dependency_key] = Provide(self._config.create_db_session_dependency)
        app_config.before_send.append(self._config.before_send_handler)
        app_config.on_shutdown.append(self._config.on_shutdown)
        app_config.initial_state.update(self._config.app_state())
        return app_config
