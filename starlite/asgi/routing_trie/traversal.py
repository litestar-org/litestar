from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Pattern, Set, Tuple

from starlite.asgi.routing_trie.types import PathParameterSentinel
from starlite.enums import ScopeType
from starlite.exceptions import MethodNotAllowedException, NotFoundException
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlite.asgi.routing_trie.types import ASGIHandlerTuple, RouteTrieNode
    from starlite.types import Scope


def traverse_route_map(
    root_node: "RouteTrieNode",
    path: str,
) -> Tuple["RouteTrieNode", List[Tuple[str, Any]], str]:
    """Traverses the application route mapping and retrieves the correct node for the request url.

    Args:
        root_node: The root trie node.
        path: The request's path.

    Raises:
         NotFoundException: if no correlating node is found.

    Returns:
        A tuple containing the target RouteMapNode and a list containing all path parameter values.
    """
    current_node = root_node
    path_params: List[Tuple[str, Any]] = []
    path_components = [p for p in path.split("/") if p]

    for i, component in enumerate(path_components):
        if component in current_node.child_keys:
            current_node = current_node.children[component]
            continue

        if current_node.path_param_definition:
            param_definition = current_node.path_param_definition
            if param_definition.type is Path:
                path_params.append((param_definition.name, normalize_path("/".join(path_components[i:]))))
                return current_node, path_params, path

            path_params.append((param_definition.name, param_definition.parser(component)))
            current_node = current_node.children[PathParameterSentinel]

        continue

    if not current_node.asgi_handlers:
        raise NotFoundException()

    return current_node, path_params, path


def parse_node_handlers(node: "RouteTrieNode", scope: "Scope") -> "ASGIHandlerTuple":
    """Retrieve the handler tuple from the node.

    Args:
        node: The trie node to parse.
        scope: The ASGI scope instance.

    Returns:
        An ASGI Handler tuple.
    """

    if node.is_asgi:
        return node.asgi_handlers["asgi"]
    if scope["type"] == ScopeType.HTTP:
        return node.asgi_handlers[scope["method"]]
    return node.asgi_handlers["websocket"]


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

    try:
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

        node, path_parameters, scope["path"] = traverse_route_map(
            root_node=root_node,
            path=normalized_path,
        )
        scope["path_params"] = dict(path_parameters)
        return parse_node_handlers(node=node, scope=scope)
    except KeyError as e:
        raise MethodNotAllowedException() from e
    except ValueError as e:
        raise NotFoundException() from e
