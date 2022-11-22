from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Pattern, Set, Tuple

from starlite.asgi.routing_trie.types import PathParameterSentinel
from starlite.exceptions import MethodNotAllowedException, NotFoundException
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlite.asgi.routing_trie.types import ASGIHandlerTuple, RouteTrieNode
    from starlite.types import ASGIApp, Method, RouteHandlerType


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


def parse_node_handlers(
    node: "RouteTrieNode",
    method: Optional["Method"],
) -> "ASGIHandlerTuple":
    """Retrieve the handler tuple from the node.

    Args:
        node: The trie node to parse.
        scope: The ASGI scope instance.

    Returns:
        An ASGI Handler tuple.
    """

    if node.is_asgi:
        return node.asgi_handlers["asgi"]
    if method:
        return node.asgi_handlers[method]
    return node.asgi_handlers["websocket"]


def parse_path_to_route(
    method: Optional["Method"],
    mount_paths_regex: Optional[Pattern],
    mount_routes: Dict[str, "RouteTrieNode"],
    path: str,
    plain_routes: Set[str],
    root_node: "RouteTrieNode",
) -> Tuple["ASGIApp", "RouteHandlerType", str, dict]:
    """Given a scope object, retrieve the asgi_handlers and is_mount boolean values from correct trie node.

    Args:
        method: The scope's method, if any.
        root_node: The root trie node.
        path: The path to resolve scope instance.
        plain_routes: The set of plain routes.
        mount_routes: Mapping of mount routes to trie nodes.
        mount_paths_regex: A compiled regex to match the mount routes.

    Raises:
        MethodNotAllowedException: if no matching method is found.

    Returns:
        A tuple containing the stack of middlewares and the route handler that is wrapped by it.
    """

    try:
        if path in plain_routes:
            asgi_app, handler = parse_node_handlers(node=root_node.children[path], method=method)
            return asgi_app, handler, path, {}

        if mount_paths_regex and (match := mount_paths_regex.search(path)):
            mount_path = path[match.start() : match.end()]
            mount_node = mount_routes[mount_path]
            remaining_path = path[match.end() :]
            # since we allow regular handlers under static paths, we must validate that the request does not match
            # any such handler.
            if not mount_node.children or not any(sub_route in path for sub_route in mount_node.children):  # type: ignore
                asgi_app, handler = parse_node_handlers(node=mount_node, method=method)
                return asgi_app, handler, remaining_path or "/", {}

        node, path_parameters, path = traverse_route_map(
            root_node=root_node,
            path=path,
        )
        asgi_app, handler = parse_node_handlers(node=node, method=method)
        return asgi_app, handler, path, dict(path_parameters)
    except KeyError as e:
        raise MethodNotAllowedException() from e
    except ValueError as e:
        raise NotFoundException() from e
