from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Sequence

from litestar._openapi.path_item import PathItemFactory
from litestar.constants import OPENAPI_NOT_INITIALIZED
from litestar.exceptions import ImproperlyConfiguredException
from litestar.routes import HTTPRoute

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.spec import OpenAPI, PathItem, Schema
    from litestar.plugins import OpenAPISchemaPluginProtocol


class OpenAPIContext:
    def __init__(
        self, openapi_config: OpenAPIConfig, plugins: Sequence[OpenAPISchemaPluginProtocol], schemas: dict[str, Schema]
    ) -> None:
        self.openapi_config = openapi_config
        self.plugins = plugins
        self.schemas = schemas


class OpenAPIFactory:
    def __init__(self, app: Litestar) -> None:
        self.app = app
        self._operation_ids: set[str] = set()
        self._initialized = False

    @cached_property
    def openapi_schema(self) -> OpenAPI:
        return self.openapi_config.to_openapi_schema()

    @cached_property
    def openapi_config(self) -> OpenAPIConfig:
        if not self.app.openapi_config:
            raise ImproperlyConfiguredException(OPENAPI_NOT_INITIALIZED)
        return self.app.openapi_config

    @cached_property
    def paths(self) -> dict[str, PathItem]:
        if self.openapi_schema.paths is None:
            raise ImproperlyConfiguredException(OPENAPI_NOT_INITIALIZED)
        return self.openapi_schema.paths

    @cached_property
    def openapi_context(self) -> OpenAPIContext:
        return OpenAPIContext(
            openapi_config=self.openapi_config,
            plugins=self.app.plugins.openapi,
            schemas=self.openapi_schema.components.schemas,
        )

    def add_route(self, route: HTTPRoute) -> None:
        if not self.app.openapi_config or not self._initialized:
            return

        if (
            any(route_handler.resolve_include_in_schema() for route_handler, _ in route.route_handler_map.values())
            and (route.path_format or "/") not in self.paths
        ):
            path_item_factory = PathItemFactory(self.openapi_context, route, self._operation_ids)
            path_item = path_item_factory.create_path_item()
            self.paths[route.path_format or "/"] = path_item
            self._operation_ids |= path_item_factory.created_operation_ids

    def initialize(self) -> None:
        if self._initialized:
            return

        if not self.app.openapi_config:
            raise ImproperlyConfiguredException(OPENAPI_NOT_INITIALIZED)

        self._initialized = True
        for route in (r for r in self.app.routes if isinstance(r, HTTPRoute)):
            self.add_route(route)
