from collections import deque
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Set, Tuple, Type, Union

from starlite.asgi.routing_trie.types import PathParameterSentinel
from starlite.enums import ScopeType
from starlite.exceptions import (
    MethodNotAllowedException,
    NotFoundException,
    ValidationException,
)
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlite.asgi.routing_trie.types import ASGIHandlerTuple, RouteTrieNode
    from starlite.types import Scope
    from starlite.types.internal_types import PathParameterDefinition


@lru_cache(maxsize=256)
def traverse_route_map(
    root_node: "RouteTrieNode",
    path: str,
) -> Tuple["RouteTrieNode", List[str], str]:
    """Traverses the application route mapping and retrieves the correct node for the request url.

    Args:
        root_node: The root trie node.
        path: The request's path.
        path_components: A list of ordered path components.
        path: request path

    Raises:
         NotFoundException: if no correlating node is found.

    Returns:
        A tuple containing the target RouteMapNode and a list containing all path parameter values.
    """
    current_node = root_node
    path_params: List[str] = []
    path_components: Deque[Union[str, Type[PathParameterSentinel]]] = deque(
        [component for component in path.split("/") if component]
    )

    while True:
        if current_node.is_mount:
            if current_node.is_static and not (path_components and path_components[0] in current_node.child_keys):
                # static paths require an ending slash.
                return current_node, path_params, normalize_path("/".join(path_components) + "/")  # type: ignore[arg-type]
            if not current_node.is_static:
                return current_node, path_params, normalize_path("/".join(path_components))  # type: ignore[arg-type]

        if current_node.is_path_type:
            path_params.append(normalize_path("/".join(path_components)))  # type: ignore[arg-type]
            return current_node, path_params, path

        has_path_param = PathParameterSentinel in current_node.child_keys

        if not path_components:
            if has_path_param or not current_node.asgi_handlers:
                raise NotFoundException()
            return current_node, path_params, path

        component = path_components.popleft()

        if component in current_node.child_keys:
            current_node = current_node.children[component]
            continue

        if has_path_param:
            path_params.append(component)  # type: ignore[arg-type]
            current_node = current_node.children[PathParameterSentinel]
            continue

        raise NotFoundException()


@lru_cache(maxsize=256)
def parse_path_parameters(
    path_parameter_definitions: Tuple["PathParameterDefinition"], request_path_parameter_values: Tuple[str]
) -> Dict[str, Any]:
    """Parse path parameters into their expected types.

    Args:
        path_parameter_definitions: A list of [PathParameterDefinition][starlite.route.base.PathParameterDefinition] instances
        request_path_parameter_values: A list of raw strings sent as path parameters as part of the request

    Raises:
        ValidationException: if path parameter parsing fails

    Returns:
        A dictionary mapping path parameter names to parsed values
    """
    try:
        return {
            param_definition.name: param_definition.parser(param)
            for param_definition, param in zip(path_parameter_definitions, request_path_parameter_values)
        }
    except ValueError as e:  # pragma: no cover
        raise ValidationException(f"unable to parse path parameters {','.join(request_path_parameter_values)}") from e


def parse_scope_to_route(root_node: "RouteTrieNode", scope: "Scope", plain_routes: Set[str]) -> "ASGIHandlerTuple":
    """Given a scope object, retrieve the asgi_handlers and is_mount boolean values from correct trie node.

    Args:
        root_node: The root trie node.
        scope: The ASGI scope instance.
        plain_routes: The set of plain routes.

    Raises:
        MethodNotAllowedException: if no matching method is found.

    Returns:
        A tuple containing the stack of middlewares and the route handler that is wrapped by it.
    """

    path = scope["path"].strip().rstrip("/") or "/"
    scope["path_params"] = {}
    try:
        if path in plain_routes:
            current_node: "RouteTrieNode" = root_node.children[path]
        else:
            current_node, path_params, path = traverse_route_map(
                root_node=root_node,
                path=path,
            )
            scope["path"] = path
            if path_params:
                scope["path_params"] = parse_path_parameters(
                    path_parameter_definitions=tuple(current_node.path_parameters),
                    request_path_parameter_values=tuple(path_params),
                )

        if current_node.is_asgi:
            return current_node.asgi_handlers["asgi"]
        if scope["type"] == ScopeType.HTTP:
            return current_node.asgi_handlers[scope["method"]]
        return current_node.asgi_handlers["websocket"]
    except KeyError as e:
        raise MethodNotAllowedException() from e
