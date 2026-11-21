from litestar import Litestar, get
from litestar.config.app import AppConfig
from litestar.di import NamedDependency, provide
from litestar.plugins import InitPlugin


@get("/", sync_to_thread=False)
def route_handler(name: NamedDependency[str]) -> dict[str, str]:
    return {"hello": name}


@provide(key="name", sync_to_thread=False)
def get_name() -> str:
    return "world"


class MyPlugin(InitPlugin):
    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.dependencies["name"] = get_name
        app_config.route_handlers.append(route_handler)
        return app_config


app = Litestar(plugins=[MyPlugin()])

# run: /
