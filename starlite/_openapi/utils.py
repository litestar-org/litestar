import re
from typing import TYPE_CHECKING, List, Union

from starlite._openapi.enums import OpenAPIType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.types.internal_types import PathParameterDefinition

__all__ = ("default_operation_id_creator", "get_openapi_type_for_complex_type", "pascal_case_to_text")


if TYPE_CHECKING:
    from starlite._signature.models import SignatureField
    from starlite.handlers.http_handlers import HTTPRouteHandler
    from starlite.types import Method

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")
SEPARATORS_CLEANUP_PATTERN = re.compile(r"[!#$%&'*+\-.^_`|~:]+")


def pascal_case_to_text(string: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'."""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, string)).strip()


def get_openapi_type_for_complex_type(field: "SignatureField") -> "OpenAPIType":
    """We are dealing with complex types in this case.

    The problem here is that the Python typing system is too crude to define OpenAPI objects properly.
    """
    if field.is_mapping:
        return OpenAPIType.OBJECT
    if field.is_non_string_sequence or field.is_non_string_iterable:
        return OpenAPIType.ARRAY

    raise ImproperlyConfiguredException(  # pragma: no cover
        f"Parameter '{field.name}' with type '{field.field_type}' could not be mapped to an Open API type. "
        f"This can occur if a user-defined generic type is resolved as a parameter. If '{field.name}' should "
        "not be documented as a parameter, annotate it using the `Dependency` function, e.g., "
        f"`{field.name}: ... = Dependency(...)`."
    )


def default_operation_id_creator(
    route_handler: "HTTPRouteHandler",
    http_method: "Method",
    path_components: List[Union[str, "PathParameterDefinition"]],
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
    for component in (c if not isinstance(c, PathParameterDefinition) else c.name for c in path_components):
        if component.title() not in components_namespace:
            components_namespace += component.title()

    return SEPARATORS_CLEANUP_PATTERN.sub("", components_namespace + handler_namespace)
