from __future__ import annotations

from typing import TYPE_CHECKING

from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.path_item import create_path_item_for_route
from litestar.exceptions import ImproperlyConfiguredException
from litestar.plugins import InitPluginProtocol
from litestar.plugins.base import ReceiveRoutePlugin
from litestar.routes import HTTPRoute

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.config.app import AppConfig
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.spec import OpenAPI
    from litestar.routes import BaseRoute


class OpenAPIPlugin(InitPluginProtocol, ReceiveRoutePlugin):
    __slots__ = (
        "app",
        "included_routes",
        "_openapi_config",
        "_openapi_schema",
    )

    def __init__(self, app: Litestar) -> None:
        self.app = app
        self.included_routes: dict[str, HTTPRoute] = {}
        self._openapi_config: OpenAPIConfig | None = None
        self._openapi_schema: OpenAPI | None = None

    def _build_openapi_schema(self) -> OpenAPI:
        openapi = self.openapi_config.to_openapi_schema()
        context = OpenAPIContext(openapi_config=self.openapi_config, plugins=self.app.plugins.openapi)
        openapi.paths = {
            route.path_format or "/": create_path_item_for_route(context, route)
            for route in self.included_routes.values()
        }
        openapi.components.schemas = context.schema_registry.generate_components_schemas()
        return openapi

    def provide_openapi(self) -> OpenAPI:
        if not self._openapi_schema:
            self._openapi_schema = self._build_openapi_schema()
        return self._openapi_schema

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        if app_config.openapi_config:
            self._openapi_config = app_config.openapi_config
            app_config.route_handlers.append(self.openapi_config.openapi_controller)
        return app_config

    @property
    def openapi_config(self) -> OpenAPIConfig:
        if not self._openapi_config:
            raise ImproperlyConfiguredException("OpenAPIConfig not initialized")
        return self._openapi_config

    def receive_route(self, route: BaseRoute) -> None:
        if not isinstance(route, HTTPRoute):
            return

        if any(route_handler.resolve_include_in_schema() for route_handler, _ in route.route_handler_map.values()):
            # Force recompute the schema if a new route is added
            self._openapi_schema = None
            self.included_routes[route.path] = route
