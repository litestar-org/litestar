"""Plugin for creating and retrieving flash messages."""

from __future__ import annotations

import contextvars
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

from litestar.exceptions import ImproperlyConfiguredException, MissingDependencyException
from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar import Request
    from litestar.config.app import AppConfig
    from litestar.middleware.session.server_side import ServerSideSessionConfig
    from litestar.template import TemplateConfig

flash_ctx_var = contextvars.ContextVar("flash_messages", default=[])


@dataclass
class FlashConfig:
    """Configuration for Flash messages."""

    template_config: TemplateConfig
    session_config: ServerSideSessionConfig | None


class FlashPlugin(InitPluginProtocol):
    """Flash messages Plugin."""

    def __init__(self, config: FlashConfig):
        """Initialize the plugin.

        Args:
            config: Configuration for flash messages, including the template engine instance.
        """
        self.config = config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Register the message callable on the template engine instance.

        Args:
            app_config: The application configuration.

        Returns:
            The application configuration with the message callable registered.
        """
        if self.config.session_config is None:
            raise ImproperlyConfiguredException("Flash messages require a session middleware.")
        template_callable: Callable[[Any], Any] = get_flashes
        with suppress(MissingDependencyException):
            from litestar.contrib.minijinja import MiniJinjaTemplateEngine, _transform_state

            if isinstance(self.config.template_config.engine_instance, MiniJinjaTemplateEngine):
                template_callable = _transform_state(get_flashes)

        self.config.template_config.engine_instance.register_template_callable("get_flashes", template_callable)  # pyright: ignore[reportGeneralTypeIssues]
        return app_config


def flash(
    request: Request,
    message: Any,
    category: str,
) -> None:
    # request.session.setdefault("_messages", []).append({"message": message, "category": category})
    current = flash_ctx_var.get()
    current.append({"message": message, "category": category})
    flash_ctx_var.set(current)


def get_flashes(context: Mapping[str, Any]) -> Any:
    # return _get_request_from_context(context).session.pop("_messages", [])
    client_addr = flash_ctx_var.get()
    flash_ctx_var.set([])
    return client_addr
