from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from litestar.config.app import AppConfig
from litestar.connection import ASGIConnection
from litestar.plugins import InitPluginProtocol
from litestar.template import TemplateConfig
from litestar.template.base import _get_request_from_context


class FlashDefaultCategory(str, Enum):
    """Default Flash message categories."""

    default = "default"
    danger = "danger"
    success = "success"


@dataclass
class FlashConfig:
    """Configuration for Flash messages."""

    template_config: TemplateConfig


class FlashPlugin(InitPluginProtocol):
    """Flash messages Plugin."""

    def __init__(self, config: FlashConfig):
        """Initialize the plugin."""
        self.config = config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Register the message callable on the template engine instance."""
        self.config.template_config.engine_instance.register_template_callable("get_flashes", get_flashes)
        return app_config


def flash(connection: ASGIConnection, message: str, category: str) -> None:
    """Add a flash message to the request scope."""
    if "_flash_messages" not in connection.state:
        connection.state["_flash_messages"] = []
    connection.state["_flash_messages"].append({"message": message, "category": category})


def get_flashes(context: Mapping[str, Any]) -> Any:
    """Get flash messages from the request scope, if any."""
    scope = _get_request_from_context(context).scope

    if "_flash_messages" in scope["state"]:
        return scope["state"]["_flash_messages"] if len(scope["state"]["_flash_messages"]) else []
    return []
