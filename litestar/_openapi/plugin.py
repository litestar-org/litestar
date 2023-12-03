from __future__ import annotations

from typing import TYPE_CHECKING, Any

from yaml import dump as dump_yaml

from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.path_item import create_path_item_for_route
from litestar.di import Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.controller import OpenAPINotFoundException
from litestar.openapi.spec import OpenAPI
from litestar.plugins import InitPluginProtocol, ReceiveRoutePluginProtocol
from litestar.response import Response
from litestar.routes import HTTPRoute
from litestar.serialization import decode_json, encode_json, get_serializer
from litestar.status_codes import HTTP_404_NOT_FOUND

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.config.app import AppConfig
    from litestar.routes import BaseRoute


class OpenAPIPlugin(InitPluginProtocol, ReceiveRoutePluginProtocol):
    def __init__(self, app: Litestar) -> None:
        self.app = app
        self.included_routes: list[HTTPRoute] = []
        self._openapi_config: OpenAPIConfig | None = None
        self._openapi_schema: OpenAPI | None = None
        self._openapi_schema_json: bytes | None = None
        self._openapi_schema_yaml: bytes | None = None

    def _build_openapi_schema(self) -> OpenAPI:
        openapi = self.openapi_config.to_openapi_schema()
        context = OpenAPIContext(
            openapi_config=self.openapi_config,
            plugins=self.app.plugins.openapi,
            schemas=openapi.components.schemas,
        )
        openapi.paths = {
            route.path_format or "/": create_path_item_for_route(context, route) for route in self.included_routes
        }
        return openapi

    def provide_openapi_schema(self) -> OpenAPI:
        if not self._openapi_schema:
            self._openapi_schema = self._build_openapi_schema()
        return self._openapi_schema

    def provide_openapi_schema_json(self) -> bytes:
        if not self._openapi_schema_json:
            self._openapi_schema_json = encode_json(
                self.provide_openapi_schema().to_schema(), get_serializer(self.app.type_encoders)
            )
        return self._openapi_schema_json

    def provide_openapi_schema_yaml(self) -> bytes:
        if not self._openapi_schema_yaml:
            schema_json = self.provide_openapi_schema_json()
            self._openapi_schema_yaml = dump_yaml(
                decode_json(schema_json),
                default_flow_style=False,
            ).encode("utf-8")
        return self._openapi_schema_yaml

    @staticmethod
    def handle_openapi_not_found(_: Any, exc: OpenAPINotFoundException) -> Response:
        return Response(content=exc.body, status_code=HTTP_404_NOT_FOUND, media_type=exc.media_type)

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        if app_config.openapi_config:
            self._openapi_config = app_config.openapi_config
            app_config.route_handlers.append(self.openapi_config.openapi_controller)
            app_config.dependencies.update(
                {
                    "openapi_schema": Provide(self.provide_openapi_schema, sync_to_thread=False),
                    "openapi_json": Provide(self.provide_openapi_schema_json, sync_to_thread=False),
                    "openapi_yaml": Provide(self.provide_openapi_schema_yaml, sync_to_thread=False),
                    "openapi_config": Provide(lambda: self.openapi_config, sync_to_thread=False),
                }
            )
            app_config.signature_types.extend([OpenAPI, OpenAPIConfig])
            app_config.exception_handlers[OpenAPINotFoundException] = self.handle_openapi_not_found
        return app_config

    @property
    def openapi_config(self) -> OpenAPIConfig:
        if not self._openapi_config:
            raise ImproperlyConfiguredException("OpenAPIConfig not initialized")
        return self._openapi_config

    def receive_route(self, route: BaseRoute) -> None:
        if not isinstance(route, HTTPRoute):
            return

        # Force recompute the schema if a new route is added
        self._openapi_schema = self._openapi_schema_yaml = self._openapi_schema_json = None

        if any(route_handler.resolve_include_in_schema() for route_handler, _ in route.route_handler_map.values()):
            self.included_routes.append(route)
