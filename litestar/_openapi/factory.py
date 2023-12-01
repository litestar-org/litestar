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
    """OpenAPI Context.

    Context object used to support OpenAPI schema generation.
    """
    __slots__ = ("openapi_config", "plugins", "schemas", "operation_ids")

    def __init__(
        self, openapi_config: OpenAPIConfig, plugins: Sequence[OpenAPISchemaPluginProtocol], schemas: dict[str, Schema]
    ) -> None:
        """Initialize OpenAPIContext.

        Args:
            openapi_config: OpenAPIConfig instance.
            plugins: OpenAPI plugins.
            schemas: Mapping of schema names to schema objects that will become the components.schemas section of the
                OpenAPI schema.
        """
        self.openapi_config = openapi_config
        self.plugins = plugins
        self.schemas = schemas
        # used to track that operation ids are globally unique across the OpenAPI document
        self.operation_ids: set[str] = set()

    def add_operation_id(self, operation_id: str) -> None:
        """Add an operation ID to the context.

        Args:
            operation_id: Operation ID to add.
        """
        if operation_id in self.operation_ids:
            raise ImproperlyConfiguredException(
                f"operation_ids must be unique, "
                f"please ensure the value of 'operation_id' is either not set or unique for {operation_id}"
            )
        self.operation_ids.add(operation_id)


class OpenAPIFactory:
    """OpenAPI Factory.

    Factory class used to support OpenAPI schema generation.
    """
    def __init__(self, app: Litestar) -> None:
        """Initialize OpenAPIFactory.

        Args:
            app: The Litestar instance.
        """
        self.app = app
        self._initialized = False

    @cached_property
    def openapi_schema(self) -> OpenAPI:
        """Return the OpenAPI schema."""
        return self.openapi_config.to_openapi_schema()

    @cached_property
    def openapi_config(self) -> OpenAPIConfig:
        """Return the OpenAPIConfig instance.

        This property exists to narrow the type of the openapi config attribute on the Factory.
        It returns the OpenAPIConfig instance, which is typed as Optional on the app, but shouldn't
        ever be None by the time it is getting called in this context.
        """
        if not self.app.openapi_config:
            raise ImproperlyConfiguredException(OPENAPI_NOT_INITIALIZED)
        return self.app.openapi_config

    @cached_property
    def paths(self) -> dict[str, PathItem]:
        """Return the OpenAPI paths.

        This property exists to narrow the type of the paths attribute on the OpenAPI schema,
        which is typed as Optional, but shouldn't ever be None at this point.
        """
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
        """Add a route to the OpenAPI schema.

        Create a `PathItem` for the route and add it to the OpenAPI schema's `paths` attribute.

        Args:
            route: The route to add.
        """
        if not self.app.openapi_config or not self._initialized:
            return

        if (
            any(route_handler.resolve_include_in_schema() for route_handler, _ in route.route_handler_map.values())
            and (route.path_format or "/") not in self.paths
        ):
            path_item_factory = PathItemFactory(self.openapi_context, route)
            path_item = path_item_factory.create_path_item()
            self.paths[route.path_format or "/"] = path_item

    def initialize(self) -> None:
        """Initialize the OpenAPIFactory.

        This method is called by the Litestar instance on first access to the OpenAPI schema.

        Before this method is called, any calls to add_route are a no-op.
        """
        if self._initialized:
            return

        if not self.app.openapi_config:
            raise ImproperlyConfiguredException(OPENAPI_NOT_INITIALIZED)

        self._initialized = True
        for route in (r for r in self.app.routes if isinstance(r, HTTPRoute)):
            self.add_route(route)
