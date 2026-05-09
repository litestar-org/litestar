from __future__ import annotations

import dataclasses
from inspect import cleandoc
from typing import TYPE_CHECKING, Any

from litestar._openapi.parameters import create_parameters_for_handler
from litestar._openapi.request_body import create_request_body
from litestar._openapi.responses import create_responses_for_handler
from litestar._openapi.utils import SEPARATORS_CLEANUP_PATTERN
from litestar.enums import HttpMethod
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import Operation, Parameter, PathItem
from litestar.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.routes import HTTPRoute

__all__ = (
    "create_path_item_for_route",
    "merge_openapi_operation",
    "merge_path_item_operations",
)


_OPERATION_FORBIDDEN_FIELDS = (
    "operation_id",
    "summary",
    "description",
    "request_body",
    "deprecated",
    "external_docs",
)


def _merge_operation_tags(target: Operation, source: Operation) -> None:
    if not source.tags:
        return
    existing_tags = list(target.tags or [])
    seen = set(existing_tags)
    for tag in source.tags:
        if tag not in seen:
            existing_tags.append(tag)
            seen.add(tag)
    target.tags = existing_tags


def _merge_operation_parameters(target: Operation, source: Operation, *, source_label: str) -> None:
    if not source.parameters:
        return
    existing_parameters = list(target.parameters or [])
    existing_keys = {(p.name, p.param_in) for p in existing_parameters if isinstance(p, Parameter)}
    for param in source.parameters:
        if isinstance(param, Parameter):
            key = (param.name, param.param_in)
            if key in existing_keys:
                raise ImproperlyConfiguredException(
                    f"OpenAPI operation parameters[{key[0]!r}, in={key[1]!r}] is already "
                    f"defined; plugin {source_label!r} cannot redefine it."
                )
            existing_keys.add(key)
        existing_parameters.append(param)
    target.parameters = existing_parameters


def _merge_operation_dict(
    target_value: dict[str, Any] | None,
    source_value: dict[str, Any] | None,
    *,
    field_name: str,
    source_label: str,
) -> dict[str, Any] | None:
    if not source_value:
        return target_value
    merged = dict(target_value or {})
    for key, value in source_value.items():
        if key in merged:
            raise ImproperlyConfiguredException(
                f"OpenAPI operation {field_name}[{key!r}] is already defined; "
                f"plugin {source_label!r} cannot redefine it."
            )
        merged[key] = value
    return merged


def merge_openapi_operation(target: Operation, source: Operation, *, source_label: str) -> None:
    """Merge a plugin-contributed :class:`Operation` fragment into the operation under construction.

    Mergeable fields:
        - ``security``: extend (additive, ordered).
        - ``tags``: extend, deduplicate while preserving first-seen order.
        - ``parameters``: extend; collisions on ``(name, param_in)`` raise.
        - ``callbacks``: dict-merge; key collisions raise.
        - ``responses``: dict-merge keyed by status code; collisions raise.

    Forbidden fields are owned by the route handler and the schema constructor; setting any
    of them raises :class:`~litestar.exceptions.ImproperlyConfiguredException`.

    Args:
        target: The operation under construction.
        source: The plugin-contributed fragment.
        source_label: Identifier for the contributing plugin, used in error messages.

    Raises:
        ImproperlyConfiguredException: ``source`` populates a forbidden field, or a
            collision occurs on ``parameters``, ``callbacks``, or ``responses``.
    """
    for field_name in _OPERATION_FORBIDDEN_FIELDS:
        if getattr(source, field_name):
            raise ImproperlyConfiguredException(
                f"OpenAPI operation field {field_name!r} is owned by the route handler; "
                f"plugin {source_label!r} cannot set it."
            )

    if source.security:
        target.security = [*(target.security or []), *source.security]

    _merge_operation_tags(target, source)
    _merge_operation_parameters(target, source, source_label=source_label)
    target.callbacks = _merge_operation_dict(
        target.callbacks, source.callbacks, field_name="callbacks", source_label=source_label
    )
    target.responses = _merge_operation_dict(
        target.responses, source.responses, field_name="responses", source_label=source_label
    )


class PathItemFactory:
    """Factory for creating a PathItem instance for a given route."""

    def __init__(self, openapi_context: OpenAPIContext, route: HTTPRoute) -> None:
        self.context = openapi_context
        self.route = route
        self._path_item = PathItem()

    def create_path_item(self) -> PathItem:
        """Create a PathItem for the given route parsing all http_methods into Operation Models.

        Returns:
            A PathItem instance.
        """
        for http_method, route_handler in self.route.route_handler_map.items():
            if not route_handler.include_in_schema:
                continue

            operation = self.create_operation_for_handler_method(route_handler, HttpMethod(http_method))

            setattr(self._path_item, http_method.lower(), operation)

        return self._path_item

    def create_operation_for_handler_method(
        self, route_handler: HTTPRouteHandler, http_method: HttpMethod
    ) -> Operation:
        """Create an Operation instance for a given route handler and http method.

        Three-phase orchestration:

        1. Collect each :class:`~litestar.plugins.OpenAPISpecPlugin`'s
           ``get_openapi_operation`` fragment exactly once and union their
           ``responses`` keys into ``plugin_owned_status_codes``.
        2. Build the operation; the response factory skips default emission for
           any status code a plugin claims, so plugin contributions do not collide
           with defaults at merge time.
        3. Merge the cached fragments into the operation via
           :func:`merge_openapi_operation`. Plugin-vs-plugin collisions still raise.

        Args:
            route_handler: A route handler instance.
            http_method: An HttpMethod enum value.

        Returns:
            An Operation instance.
        """
        plugin_fragments: list[tuple[Any, Operation]] = []
        plugin_owned_status_codes: set[str] = set()
        for plugin in self.context.openapi_spec:
            fragment = plugin.get_openapi_operation(route_handler)
            if fragment is None:
                continue
            plugin_fragments.append((plugin, fragment))
            if fragment.responses:
                plugin_owned_status_codes.update(fragment.responses.keys())

        operation_id = self.create_operation_id(route_handler, http_method)
        parameters = create_parameters_for_handler(self.context, route_handler, self.route.path_parameters)
        signature_fields = route_handler.parsed_fn_signature.parameters

        request_body = None
        if data_field := signature_fields.get("data"):
            request_body = create_request_body(
                self.context, route_handler.handler_id, route_handler.data_dto, data_field
            )

        raises_validation_error = bool(data_field or self._path_item.parameters or parameters)
        responses = create_responses_for_handler(
            self.context,
            route_handler,
            raises_validation_error=raises_validation_error,
            plugin_owned_status_codes=plugin_owned_status_codes or None,
        )

        operation = route_handler.operation_class(
            operation_id=operation_id,
            tags=sorted(route_handler.tags) if route_handler.tags else None,
            summary=route_handler.summary or SEPARATORS_CLEANUP_PATTERN.sub("", route_handler.handler_name.title()),
            description=self.create_description_for_handler(route_handler),
            deprecated=route_handler.deprecated,
            responses=responses,
            request_body=request_body,
            parameters=parameters or None,  # type: ignore[arg-type]
            security=list(route_handler.security) or None,
        )
        for plugin, fragment in plugin_fragments:
            merge_openapi_operation(operation, fragment, source_label=type(plugin).__name__)
        return operation

    def create_operation_id(self, route_handler: HTTPRouteHandler, http_method: HttpMethod) -> str:
        """Create an operation id for a given route handler and http method.

        Adds the operation id to the context's operation id set, where it is checked for uniqueness.

        Args:
            route_handler: A route handler instance.
            http_method: An HttpMethod enum value.

        Returns:
            An operation id string.
        """
        if isinstance(route_handler.operation_id, str):
            operation_id = route_handler.operation_id
        elif callable(route_handler.operation_id):
            operation_id = route_handler.operation_id(route_handler, http_method, self.route.path_components)
        else:
            operation_id = self.context.openapi_config.operation_id_creator(
                route_handler, http_method, self.route.path_components
            )
        self.context.add_operation_id(operation_id)
        return operation_id

    def create_description_for_handler(self, route_handler: HTTPRouteHandler) -> str | None:
        """Produce the operation description for a route handler.

        Args:
            route_handler: A route handler instance.

        Returns:
            An optional description string
        """
        handler_description = route_handler.description
        if handler_description is None and self.context.openapi_config.use_handler_docstrings:
            fn = unwrap_partial(route_handler.fn)
            return cleandoc(fn.__doc__) if fn.__doc__ else None
        return handler_description


def create_path_item_for_route(openapi_context: OpenAPIContext, route: HTTPRoute) -> PathItem:
    """Create a PathItem for the given route parsing all http_methods into Operation Models.

    Args:
        openapi_context: The OpenAPIContext instance.
        route: The route to create a PathItem for.

    Returns:
        A PathItem instance.
    """
    path_item_factory = PathItemFactory(openapi_context, route)
    return path_item_factory.create_path_item()


def merge_path_item_operations(source: PathItem, other: PathItem, for_path: str) -> PathItem:
    """Merge operations from path items, creating a new path item that includes
    operations from both.
    """
    attrs_to_merge = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
    fields = {f.name for f in dataclasses.fields(PathItem)} - attrs_to_merge
    if any(getattr(source, attr) and getattr(other, attr) for attr in attrs_to_merge):
        raise ValueError("Cannot merge operation for PathItem if operation is set on both items")

    if differing_values := [
        (value_a, value_b) for attr in fields if (value_a := getattr(source, attr)) != (value_b := getattr(other, attr))
    ]:
        raise ImproperlyConfiguredException(
            f"Conflicting OpenAPI path configuration for {for_path!r}. "
            f"{', '.join(f'{a} != {b}' for a, b in differing_values)}"
        )

    return dataclasses.replace(
        source,
        get=source.get or other.get,
        post=source.post or other.post,
        patch=source.patch or other.patch,
        put=source.put or other.put,
        delete=source.delete or other.delete,
        options=source.options or other.options,
        trace=source.trace or other.trace,
    )
