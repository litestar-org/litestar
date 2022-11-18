from collections import deque
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    List,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    Union,
)

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
        component for component in path.split("/") if component
    )

    while True:
        if path_components:
            component = path_components.popleft()

            if component in current_node.child_keys:
                current_node = current_node.children[component]
                continue

            if PathParameterSentinel in current_node.child_keys:
                if current_node.is_path_type:
                    path_params.append(normalize_path("/".join(path_components)))  # type: ignore[arg-type]
                    return current_node, path_params, path

                path_params.append(component)  # type: ignore[arg-type]
                current_node = current_node.children[PathParameterSentinel]

            continue

        if not current_node.asgi_handlers:
            raise NotFoundException()

        return current_node, path_params, path

        # raise NotFoundException()


def parse_path_parameters(
    path_parameter_definitions: List["PathParameterDefinition"], request_path_parameter_values: List[str]
) -> Dict[str, Any]:
    """Parse path parameters into their expected types.

    Args:
        path_parameter_definitions: A tuple of [PathParameterDefinition][starlite.route.base.PathParameterDefinition] instances
        request_path_parameter_values: A tuple of raw strings sent as path parameters as part of the request

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


def parse_node_handlers(node: "RouteTrieNode", scope: "Scope") -> "ASGIHandlerTuple":
    """Retrieve the handler tuple from the node.

    Args:
        node: The trie node to parse.
        scope: The ASGI scope instance.

    Returns:
        An ASGI Handler tuple.
    """
    try:
        if node.is_asgi:
            return node.asgi_handlers["asgi"]
        if scope["type"] == ScopeType.HTTP:
            return node.asgi_handlers[scope["method"]]
        return node.asgi_handlers["websocket"]
    except KeyError as e:
        raise MethodNotAllowedException() from e


def parse_scope_to_route(
    root_node: "RouteTrieNode",
    scope: "Scope",
    plain_routes: Set[str],
    mount_routes: Dict[str, "RouteTrieNode"],
    mount_paths_regex: Optional[Pattern],
) -> "ASGIHandlerTuple":
    """Given a scope object, retrieve the asgi_handlers and is_mount boolean values from correct trie node.

    Args:
        root_node: The root trie node.
        scope: The ASGI scope instance.
        plain_routes: The set of plain routes.
        mount_routes: Mapping of mount routes to trie nodes.
        mount_paths_regex: A compiled regex to match the mount routes.

    Raises:
        MethodNotAllowedException: if no matching method is found.

    Returns:
        A tuple containing the stack of middlewares and the route handler that is wrapped by it.
    """

    scope["path_params"] = {}
    normalized_path = normalize_path(scope["path"])

    if normalized_path in plain_routes:
        return parse_node_handlers(node=root_node.children[normalized_path], scope=scope)

    if mount_paths_regex and mount_paths_regex.search(normalized_path):
        mount_path = mount_paths_regex.findall(normalized_path)[0]
        mount_node = mount_routes[mount_path]
        remaining_path = normalized_path.replace(mount_path, "", 1)
        # since we allow regular handlers under static paths, we must validate that the request does not match
        # any such handler.
        if not mount_node.children or not any(sub_route in normalized_path for sub_route in mount_node.children):  # type: ignore
            scope["path"] = remaining_path or "/"
            return parse_node_handlers(node=mount_node, scope=scope)

    node, path_params, processed_path = traverse_route_map(
        root_node=root_node,
        path=normalized_path,
    )
    scope["path"] = processed_path
    if path_params:
        scope["path_params"] = parse_path_parameters(
            path_parameter_definitions=node.path_parameters,
            request_path_parameter_values=path_params,
        )
    return parse_node_handlers(node=node, scope=scope)
