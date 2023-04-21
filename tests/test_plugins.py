from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import MediaType, get
from litestar.plugins import InitPluginProtocol
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.datastructures import State


@get("/", media_type=MediaType.TEXT)
def greet() -> str:
    return "hello world"


def test_plugin_on_app_init() -> None:
    tag = "on_app_init_called"

    def on_startup(state: State) -> None:
        state.called = True

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
