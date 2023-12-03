from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.path_item import create_path_item_for_route
from litestar.constants import OPENAPI_NOT_INITIALIZED
from litestar.exceptions import ImproperlyConfiguredException
from litestar.routes import HTTPRoute

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.spec import OpenAPI, PathItem


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
            self.paths[route.path_format or "/"] = create_path_item_for_route(self.openapi_context, route)

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
