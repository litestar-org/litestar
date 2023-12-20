from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.path_item import create_path_item_for_route
from litestar.di import Provide
from litestar.enums import MediaType
from litestar.exceptions import ImproperlyConfiguredException, NotFoundException
from litestar.handlers import get
from litestar.plugins import InitPluginProtocol
from litestar.plugins.base import ReceiveRoutePlugin
from litestar.response import Response
from litestar.router import Router
from litestar.routes import HTTPRoute
from litestar.status_codes import HTTP_404_NOT_FOUND

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.config.app import AppConfig
    from litestar.connection import Request
    from litestar.handlers import HTTPRouteHandler
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.plugins import OpenAPIRenderPlugin
    from litestar.openapi.spec import OpenAPI
    from litestar.routes import BaseRoute


def handle_schema_path_not_found(path: str = "/") -> Response:
    """Handler for returning HTML formatted errors from not-found schema paths.

    This preserves backward compatibility with the Controller-based OpenAPI implementation.
    """
    if path.endswith((".json", ".yaml", ".yml")):
        raise NotFoundException

    content = b"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>404 Not found</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <h1>Error 404</h1>
        </body>
    </html>
    """
    return Response(content, media_type=MediaType.HTML, status_code=HTTP_404_NOT_FOUND)


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

    def _build_openapi(self) -> OpenAPI:
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
            self._openapi_schema = self._build_openapi()
        return self._openapi_schema

    def provide_openapi_schema(self) -> Dict[str, Any]:  # noqa: UP006
        return self.provide_openapi().to_schema()

    def create_openapi_router(self) -> Router:
        root_configured = False

        def create_handler(plugin: OpenAPIRenderPlugin) -> HTTPRouteHandler:
            paths = [plugin.path] if isinstance(plugin.path, str) else list(plugin.path)
            if any(path.endswith(self.openapi_config.root_schema_site) for path in paths):
                nonlocal root_configured
                root_configured = True
                paths.append("/")

            @get(paths, media_type=plugin.media_type, sync_to_thread=False)
            def _handler(request: Request, __openapi_schema: Dict[str, Any]) -> bytes:  # noqa: UP006
                return plugin.render(request, __openapi_schema)

            return _handler

        not_found_handler_paths = ["/{path:str}"]
        if not root_configured:
            not_found_handler_paths.append("/")

        not_found_handler = get(not_found_handler_paths, media_type=MediaType.HTML, sync_to_thread=False)(
            handle_schema_path_not_found
        )

        router = Router(
            self.openapi_config.path or "/schema",
            route_handlers=[
                *(create_handler(plugin) for plugin in self.openapi_config.render_plugins),
                not_found_handler,
            ],
            include_in_schema=False,
            dto=None,
            return_dto=None,
        )
        for plugin in self.openapi_config.render_plugins:
            plugin.receive_router(router)

        return router

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        if app_config.openapi_config:
            self._openapi_config = app_config.openapi_config
            if (controller := app_config.openapi_config.openapi_controller) is not None:
                app_config.route_handlers.append(controller)
            else:
                app_config.dependencies["_OpenAPIPlugin__openapi_schema"] = Provide(
                    self.provide_openapi_schema, use_cache=True, sync_to_thread=False
                )
                app_config.route_handlers.append(self.create_openapi_router())
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
