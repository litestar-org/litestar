from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVarTuple, get_args, get_origin

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types.internal_types import PathParameterDefinition
from litestar.typing import FieldDefinition, TypeAliasTypes
from litestar.utils.typing import _substitute_typevars

if TYPE_CHECKING:
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.types import Method


__all__ = (
    "SEPARATORS_CLEANUP_PATTERN",
    "default_operation_id_creator",
    "default_schema_component_name_creator",
    "get_parametrized_generic_class",
    "is_recursive_type_alias",
    "is_type_alias",
    "resolve_type_alias",
    "supports_openapi_3_2",
)

SEPARATORS_CLEANUP_PATTERN = re.compile(r"[!#$%&'*+\-.^_`|~:]+")


def default_operation_id_creator(
    route_handler: HTTPRouteHandler,
    http_method: Method,
    path_components: list[str | PathParameterDefinition],
) -> str:
    """Create a unique 'operationId' for an OpenAPI PathItem entry.

    Args:
        route_handler: The HTTP Route Handler instance.
        http_method: The HTTP method for the given PathItem.
        path_components: A list of path components.

    Returns:
        A camelCased operationId created from the handler function name,
        http method and path components.
    """

    handler_namespace = (
        http_method.title() + route_handler.handler_name.title()
        if len(route_handler.http_methods) > 1
        else route_handler.handler_name.title()
    )

    components_namespace = ""
    for component in (c.name if isinstance(c, PathParameterDefinition) else c for c in path_components):
        if component.title() not in components_namespace:
            components_namespace += component.title()

    return SEPARATORS_CLEANUP_PATTERN.sub("", components_namespace + handler_namespace)


def default_schema_component_name_creator(field_definition: FieldDefinition) -> str:
    """Create the name of the component schema of a type.

    Args:
        field_definition: The type the component schema describes.

    Returns:
        The qualified name of the type, followed by the names of its type arguments if it is a parametrized generic,
        e.g. ``Page_Item`` for ``Page[Item]``.
    """
    annotation = field_definition.annotation
    origin, inner_types = field_definition.origin, field_definition.inner_types
    if generic := get_parametrized_generic_class(annotation):
        origin, inner_types = generic[0], tuple(FieldDefinition.from_annotation(arg) for arg in generic[1])

    if inner_types and origin is not None:
        name = "Union" if field_definition.is_union else getattr(origin, "__qualname__", None) or str(origin)
        return "_".join((name, *(default_schema_component_name_creator(t) for t in inner_types))).replace(
            ".<locals>.", "."
        )
    if field_definition.is_none_type:
        return "None"
    return (getattr(annotation, "__qualname__", None) or str(annotation)).replace(".<locals>.", ".")


def get_parametrized_generic_class(annotation: Any) -> tuple[type, tuple[Any, ...]] | None:
    """Return the generic class and type arguments of a class created by parametrizing a generic model.

    Parametrizing a generic Pydantic model creates a new class instead of a generic alias, which does not expose
    its type arguments the way an alias does.
    """
    metadata = getattr(annotation, "__pydantic_generic_metadata__", None)
    if metadata and metadata.get("origin") and metadata.get("args"):
        return metadata["origin"], tuple(metadata["args"])
    return None


def supports_openapi_3_2(openapi_version: str) -> bool:
    """Return whether ``openapi_version`` is version 3.2 of the OpenAPI Specification or newer."""
    major, minor, *_ = openapi_version.split(".")
    return (int(major), int(minor)) >= (3, 2)


def is_type_alias(annotation: Any) -> bool:
    """Return whether the annotation is a PEP 695 type alias, subscripted or not."""
    return isinstance(annotation, TypeAliasTypes) or isinstance(get_origin(annotation), TypeAliasTypes)


def resolve_type_alias(annotation: Any) -> Any:
    """Return the value of a type alias, with the type parameters replaced by the subscript's arguments."""
    if isinstance(annotation, TypeAliasTypes):
        return annotation.__value__
    alias = get_origin(annotation)
    type_params = alias.__type_params__
    if any(isinstance(type_param, (ParamSpec, TypeVarTuple)) for type_param in type_params):
        raise ImproperlyConfiguredException(
            f"Cannot generate a schema for {annotation!r}: type aliases with a TypeVarTuple or ParamSpec type "
            "parameter cannot be subscripted in a documented type"
        )
    typevar_map = dict(zip(type_params, get_args(annotation), strict=False))
    for type_param in type_params[len(typevar_map) :]:
        if getattr(type_param, "has_default", bool)():
            typevar_map[type_param] = type_param.__default__
    return _substitute_typevars(alias.__value__, typevar_map)


def is_recursive_type_alias(annotation: Any) -> bool:
    """Return whether the value of a type alias refers back to the alias, directly or through other aliases."""
    seen: set[Any] = set()

    def visit(current: Any) -> bool:
        if is_type_alias(current):
            if current == annotation:
                return True
            if current in seen:
                return False
            seen.add(current)
            return visit(resolve_type_alias(current))
        return any(visit(arg) for arg in get_args(current))

    try:
        return visit(resolve_type_alias(annotation))
    except RecursionError as exc:
        raise ImproperlyConfiguredException(
            f"Cannot generate a schema for {annotation!r}: the type alias expands to ever larger types"
        ) from exc
