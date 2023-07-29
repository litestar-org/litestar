from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.contrib.sqlalchemy.plugins import _slots_base
from litestar.di import Provide
from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

    from .config import SQLAlchemyAsyncConfig, SQLAlchemySyncConfig

__all__ = ("SQLAlchemyInitPlugin",)


class SQLAlchemyInitPlugin(InitPluginProtocol, _slots_base.SlotsBase):
    """SQLAlchemy application lifecycle configuration."""

    def __init__(self, config: SQLAlchemyAsyncConfig | SQLAlchemySyncConfig) -> None:
        """Initialize ``SQLAlchemyPlugin``.

        Args:
            config: configure DB connection and hook handlers and dependencies.
        """
        self._config = config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with SQLAlchemy.

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """
        app_config.dependencies.update(
            {
                self._config.engine_dependency_key: Provide(self._config.provide_engine, sync_to_thread=False),
                self._config.session_dependency_key: Provide(self._config.provide_session, sync_to_thread=False),
            }
        )
        app_config.before_send.append(self._config.before_send_handler)
        app_config.on_startup.insert(0, self._config.update_app_state)
        app_config.on_shutdown.append(self._config.on_shutdown)
        app_config.signature_namespace.update(self._config.signature_namespace)
        return app_config
