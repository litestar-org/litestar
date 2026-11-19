from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING, Any

from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.path_item import OPERATION_FIELDS, PathItemFactory, merge_path_item_operations
from litestar._openapi.schema_generation.unions import use_any_of_if_overlapping
from litestar._openapi.utils import supports_openapi_3_2
from litestar.constants import OPENAPI_JSON_HANDLER_NAME
from litestar.enums import HttpMethod, MediaType
from litestar.exceptions import ImproperlyConfiguredException, NotFoundException
from litestar.handlers import get
from litestar.openapi.plugins import JsonRenderPlugin
from litestar.openapi.spec import (
    XML,
    BaseSchemaObject,
    Components,
    Discriminator,
    Example,
    OAuthFlow,
    OAuthFlows,
    OpenAPIMediaType,
    OpenAPIResponse,
    Parameter,
    PathItem,
    Schema,
    SecurityScheme,
    Server,
    Tag,
)
from litestar.plugins import InitPlugin
from litestar.plugins.base import ReceiveRoutePlugin
from litestar.response import Response
from litestar.router import Router
from litestar.routes import HTTPRoute
from litestar.status_codes import HTTP_404_NOT_FOUND

if TYPE_CHECKING:
    from collections.abc import Iterator

    from litestar.app import Litestar
    from litestar.config.app import AppConfig
    from litestar.connection import Request
    from litestar.handlers import HTTPRouteHandler
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.plugins import OpenAPIRenderPlugin
    from litestar.openapi.spec import OpenAPI
    from litestar.params import FromPath
    from litestar.routes import BaseRoute

_PATH_PARAMETER_PATTERN = re.compile(r"{([^}]*)}")
_OPENAPI_3_2_FIELDS: dict[type[BaseSchemaObject], tuple[str, ...]] = {
    Components: ("media_types",),
    Discriminator: ("default_mapping",),
    Example: ("data_value", "serialized_value"),
    OAuthFlow: ("device_authorization_url",),
    OAuthFlows: ("device_authorization",),
    OpenAPIMediaType: ("item_schema", "prefix_encoding", "item_encoding"),
    OpenAPIResponse: ("summary",),
    PathItem: ("query", "additional_operations"),
    SecurityScheme: ("oauth2_metadata_url", "deprecated"),
    Server: ("name",),
    Tag: ("summary", "parent", "kind"),
    XML: ("node_type",),
}
_CONTAINERS = (BaseSchemaObject, list, tuple, dict)
_FIELD_NAMES: dict[type, tuple[str, ...]] = {}


def _iter_spec_objects(root: OpenAPI) -> Iterator[BaseSchemaObject]:
    seen: set[int] = set()
    stack: list[Any] = [root]
    while stack:
        value = stack.pop()
        if isinstance(value, BaseSchemaObject):
            if id(value) in seen:
                continue
            seen.add(id(value))
            yield value
            if (names := _FIELD_NAMES.get(type(value))) is None:
                names = _FIELD_NAMES[type(value)] = tuple(field.name for field in dataclasses.fields(value))
            for name in names:
                if (item := getattr(value, name)) is not None and isinstance(item, _CONTAINERS):
                    stack.append(item)
        else:
            stack.extend(
                item
                for item in (value.values() if isinstance(value, dict) else value)
                if item is not None and isinstance(item, _CONTAINERS)
            )


def _finalize_document(openapi: OpenAPI, openapi_version: str) -> None:
    """Turn overlapping ``oneOf`` into ``anyOf`` and reject fields an OpenAPI 3.1 document can't contain."""
    components = openapi.components.schemas or {}
    check_fields = not supports_openapi_3_2(openapi_version)
    newer_fields: set[str] = set()
    for value in _iter_spec_objects(openapi):
        if isinstance(value, Schema):
            use_any_of_if_overlapping(value, components)
        elif check_fields and (field_names := _OPENAPI_3_2_FIELDS.get(type(value))):
            newer_fields.update(
                f"{type(value).__name__}.{name}" for name in field_names if getattr(value, name) is not None
            )
    if newer_fields:
        raise ImproperlyConfiguredException(
            f"{', '.join(sorted(newer_fields))} require 'openapi_version' to be 3.2.0 or newer, "
            f"the document is generated as {openapi_version}"
        )


def _rename_path_parameters(path_item: PathItem, names: dict[str, str]) -> PathItem:
    operations = {}
    for field_name in OPERATION_FIELDS:
        if (operation := getattr(path_item, field_name)) is not None and operation.parameters:
            parameters = [
                dataclasses.replace(parameter, name=names[parameter.name])
                if isinstance(parameter, Parameter) and parameter.param_in == "path" and parameter.name in names
                else parameter
                for parameter in operation.parameters
            ]
            operations[field_name] = dataclasses.replace(operation, parameters=parameters)
    return dataclasses.replace(path_item, **operations)


def handle_schema_path_not_found(path: FromPath[str] = "/") -> Response:
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


class OpenAPIPlugin(InitPlugin, ReceiveRoutePlugin):
    __slots__ = (
        "_documented_operations",
        "_openapi",
        "_openapi_config",
        "_openapi_schema",
        "app",
        "included_routes",
    )

    def __init__(self, app: Litestar) -> None:
        self.app = app
        self.included_routes: dict[str, HTTPRoute] = {}
        self._openapi_config: OpenAPIConfig | None = None
        self._openapi: OpenAPI | None = None
        self._openapi_schema: dict[str, object] | None = None
        self._documented_operations: dict[tuple[str, str], tuple[str, HTTPRouteHandler]] = {}

    def _build_openapi(self) -> OpenAPI:
        openapi_config = self.openapi_config

        if openapi_config.create_examples:
            from litestar._openapi.schema_generation.examples import ExampleFactory

            ExampleFactory.seed_random(openapi_config.random_seed)

        openapi = openapi_config.to_openapi_schema()
        context = OpenAPIContext(openapi_config=openapi_config, plugins=self.app.plugins.openapi)
        path_items: dict[str, PathItem] = {}
        documented: set[tuple[str, str]] = set()
        documented_paths: dict[str, str] = {}
        route_path_items: list[tuple[HTTPRoute, str, str, PathItem]] = []
        for route in self.included_routes.values():
            path_item = PathItemFactory(context, route).create_path_item()
            if path_item == PathItem():
                continue
            route_path = route.path_format or "/"
            template = _PATH_PARAMETER_PATTERN.sub("{}", route_path)
            documented_paths[template] = min(documented_paths.get(template, route_path), route_path)
            route_path_items.append((route, route_path, template, path_item))

        route_path_items.sort(key=lambda item: item[1] != documented_paths[item[2]])
        for route, route_path, template, path_item in route_path_items:
            for http_method in route.route_handler_map:
                if getattr(path_item, http_method.lower(), None) is None:
                    continue
                if (template, http_method) in documented:
                    path_item = dataclasses.replace(path_item, **{http_method.lower(): None})
                documented.add((template, http_method))
            path = documented_paths[template]
            if path != route_path:
                names = zip(
                    _PATH_PARAMETER_PATTERN.findall(route_path), _PATH_PARAMETER_PATTERN.findall(path), strict=True
                )
                path_item = _rename_path_parameters(path_item, dict(names))
            if existing_path_item := path_items.get(path):
                path_item = merge_path_item_operations(existing_path_item, path_item, for_path=path)
            path_items[path] = path_item

        openapi.paths = path_items
        openapi.components.schemas = context.schema_registry.generate_components_schemas()
        _finalize_document(openapi, openapi_config.openapi_version)
        return openapi

    def invalidate_schema_cache(self) -> None:
        if self._openapi_config is None:
            raise ImproperlyConfiguredException("OpenAPIConfig not initialized")
        self._openapi = None
        self._openapi_schema = None

    def provide_openapi(self) -> OpenAPI:
        if not self._openapi:
            self._openapi = self._build_openapi()
        return self._openapi

    def provide_openapi_schema(self) -> dict[str, Any]:
        if not self._openapi_schema:
            self._openapi_schema = self.provide_openapi().to_schema()
        return self._openapi_schema

    def create_openapi_router(self) -> Router:
        """Create a router for serving OpenAPI documentation and schema files.

        For each OpenAPI render plugin, a route is created to serve the plugin's
        documentation site.

        A handler is added for serving a 404 page for any schema path that is not
        configured by a plugin.

        A handler is added for serving the JSON OpenAPI schema file if it is not configured.

        For each plugin, the plugin's `receive_router` method is called with the router
        instance.

        Returns:
            The router.
        """
        if (router := self.openapi_config.openapi_router) is None:
            router = Router(
                self.openapi_config.path or "/schema",
                route_handlers=[],
                include_in_schema=False,
                dto=None,
                return_dto=None,
            )

        root_configured = False
        openapi_json_found = False

        def create_handler(plugin_: OpenAPIRenderPlugin) -> HTTPRouteHandler:
            """Create a handler for serving the plugin's documentation site.

            If the plugin is the default plugin, a handler is created for the root path in addition
            to the plugin's configured paths.

            If the plugin has a path for serving the OpenAPI schema file, the `openapi_json_found`
            flag is set to `True`, so that we don't create a handler for serving the JSON schema file.

            Args:
                plugin_: The plugin to create the handler for.

            Returns:
                The handler.
            """
            paths = list(plugin_.paths)
            if plugin_ is self.openapi_config.default_plugin:
                if not plugin_.has_path("/"):
                    paths.append("/")
                nonlocal root_configured
                root_configured = True

            handler_name = None
            if plugin_.has_path("/openapi.json"):
                nonlocal openapi_json_found
                openapi_json_found = True
                handler_name = OPENAPI_JSON_HANDLER_NAME

            @get(paths, media_type=plugin_.media_type, sync_to_thread=False, name=handler_name)
            def _handler(request: Request) -> bytes:
                return plugin_.render(request, self.provide_openapi_schema())

            return _handler

        for plugin in self.openapi_config.render_plugins:
            router.register(create_handler(plugin))

        not_found_handler_paths = ["/{path:str}"]
        if not root_configured:
            not_found_handler_paths.append("/")

        not_found_handler = get(not_found_handler_paths, media_type=MediaType.HTML, sync_to_thread=False)(
            handle_schema_path_not_found
        )
        router.register(not_found_handler)

        if not openapi_json_found:
            router.register(create_handler(JsonRenderPlugin()))

        for plugin in self.openapi_config.render_plugins:
            plugin.receive_router(router)

        return router

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        if app_config.openapi_config:
            self._openapi_config = app_config.openapi_config
            app_config.route_handlers.append(self.create_openapi_router())
        return app_config

    @property
    def openapi_config(self) -> OpenAPIConfig:
        if not self._openapi_config:
            raise ImproperlyConfiguredException("OpenAPIConfig not initialized")
        return self._openapi_config

    def _check_documented_operations(self, route: HTTPRoute, openapi_config: OpenAPIConfig) -> None:
        template = _PATH_PARAMETER_PATTERN.sub("{}", route.path_format or "/")
        for http_method, route_handler in route.route_handler_map.items():
            if not route_handler.include_in_schema or (
                http_method == HttpMethod.QUERY and not supports_openapi_3_2(openapi_config.openapi_version)
            ):
                continue
            other_path, other_handler = self._documented_operations.setdefault(
                (template, http_method), (route.path, route_handler)
            )
            if other_path != route.path and other_handler is not route_handler:
                raise ImproperlyConfiguredException(
                    f"Route handlers '{other_handler}' and '{route_handler}' both serve {http_method} on paths that "
                    f"differ only in their path parameters, registered as {other_path!r} and {route.path!r}. Only "
                    "one of the handlers can be reached, and OpenAPI does not allow two such operations."
                )

    def receive_route(self, route: BaseRoute) -> None:
        if not isinstance(route, HTTPRoute):
            return

        if self._openapi_config is not None:
            self._check_documented_operations(route, self._openapi_config)

        if any(route_handler.include_in_schema for route_handler in route.route_handler_map.values()):
            # Force recompute the schema if a new route is added
            self._openapi = None
            self._openapi_schema = None
            self.included_routes[route.path] = route
