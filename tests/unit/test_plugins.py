from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click import Group

from litestar import Litestar, MediaType, get
from litestar.contrib.pydantic import PydanticInitPlugin, PydanticSchemaPlugin
from litestar.contrib.sqlalchemy.plugins import SQLAlchemySerializationPlugin
from litestar.plugins import CLIPluginProtocol, InitPluginProtocol, PluginRegistry
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


def test_plugin_on_app_init() -> None:
    @get("/", media_type=MediaType.TEXT)
    def greet() -> str:
        return "hello world"

    tag = "on_app_init_called"

    def on_startup(app: Litestar) -> None:
        app.state.called = True

    class PluginWithInitOnly(InitPluginProtocol):
        def on_app_init(self, app_config: AppConfig) -> AppConfig:
            app_config.tags.append(tag)
            app_config.on_startup.append(on_startup)
            app_config.route_handlers.append(greet)
            return app_config

    with create_test_client(plugins=[PluginWithInitOnly()]) as client:
        response = client.get("/")
        assert response.text == "hello world"

        assert tag in client.app.tags
        assert client.app.state.called


def test_plugin_registry() -> None:
    class CLIPlugin(CLIPluginProtocol):
        def on_cli_init(self, cli: Group) -> None:
            pass

    cli_plugin = CLIPlugin()
    serialization_plugin = SQLAlchemySerializationPlugin()
    openapi_plugin = PydanticSchemaPlugin()
    init_plugin = PydanticInitPlugin()

    registry = PluginRegistry([cli_plugin, serialization_plugin, openapi_plugin, init_plugin])

    assert registry.openapi == (openapi_plugin,)
    assert registry.cli == (cli_plugin,)
    assert registry.serialization == (serialization_plugin,)
    assert registry.init == (init_plugin,)

    assert openapi_plugin in registry
    assert serialization_plugin in registry
    assert init_plugin in registry
    assert cli_plugin in registry

    assert set(registry) == {openapi_plugin, cli_plugin, init_plugin, serialization_plugin}


def test_plugin_registry_get() -> None:
    class CLIPlugin(CLIPluginProtocol):
        def on_cli_init(self, cli: Group) -> None:
            pass

    cli_plugin = CLIPlugin()

    with pytest.raises(KeyError, match="No plugin of type 'CLIPlugin' registered"):
        PluginRegistry([]).get(CLIPlugin)

    assert PluginRegistry([cli_plugin]).get(CLIPlugin) is cli_plugin
