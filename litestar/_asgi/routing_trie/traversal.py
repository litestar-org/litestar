from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from litestar._asgi.routing_trie.types import PathParameterSentinel
from litestar.exceptions import ClientException, MethodNotAllowedException, NotFoundException
from litestar.utils import normalize_path

__all__ = ("parse_node_handlers", "parse_path_params", "parse_path_to_route", "traverse_route_map")


if TYPE_CHECKING:
    from re import Pattern

    from litestar._asgi.routing_trie.types import ASGIHandlerTuple, RouteTrieNode
    from litestar.types import ASGIApp, Method, RouteHandlerType
    from litestar.types.internal_types import PathParameterDefinition


def traverse_route_map(
    root_node: RouteTrieNode,
    path: str,
) -> tuple[RouteTrieNode, list[str], str]:
    """Traverses the application route mapping and retrieves the correct node for the request url.

    Args:
        root_node: The root trie node.
        path: The request's path.

    Raises:
        NotFoundException: If no correlating node is found.

    Returns:
        A tuple containing the target RouteMapNode and a list containing all path parameter values.
    """
    path_components = [p for p in path.split("/") if p]
    matched = _traverse_node(root_node, path_components, [])
    if matched is None:
        raise NotFoundException()

    current_node, path_params = matched
    if not current_node.asgi_handlers:
        raise NotFoundException()

    return current_node, path_params, path


def _traverse_node(
    node: RouteTrieNode,
    components: list[str],
    path_params: list[str],
) -> tuple[RouteTrieNode, list[str]] | None:
    """Walk one trie node, backtracking when a greedy ``{path:path}`` would hide a more specific route."""
    if not components:
        return (node, path_params) if node.asgi_handlers else None

    component = components[0]
    remaining = components[1:]

    if component in node.child_keys:
        matched = _traverse_node(node.children[component], remaining, path_params)
        if matched is not None:
            return matched

    if not node.is_path_param_node:
        return None

    param_node = node.children[PathParameterSentinel]
    if param_node.is_path_type:
        # Try children of the catch-all node (e.g. ``{slug}/hello``) before
        # consuming the rest of the path. Skip when nothing remains: an empty
        # continuation would bind the catch-all handler to a raw segment
        # instead of a normalised path.
        if remaining:
            matched = _traverse_node(param_node, remaining, [*path_params, component])
            if matched is not None:
                return matched
        if param_node.asgi_handlers:
            return param_node, [*path_params, normalize_path("/".join(components))]
        return None

    return _traverse_node(param_node, remaining, [*path_params, component])


def parse_node_handlers(
    node: RouteTrieNode,
    method: Method | None,
) -> ASGIHandlerTuple:
    """Retrieve the handler tuple from the node.

    Args:
        node: The trie node to parse.
        method: The scope's method.

    Raises:
        KeyError: If no matching method is found.

    Returns:
        An ASGI Handler tuple.
    """

    if node.is_asgi:
        return node.asgi_handlers["asgi"]
    if method:
        try:
            return node.asgi_handlers[method]
        except KeyError as e:
            raise MethodNotAllowedException(headers={"allow": ", ".join(node.asgi_handlers.keys())}) from e
    try:
        return node.asgi_handlers["websocket"]
    except KeyError as e:
        raise ClientException() from e


@lru_cache(1024)
def parse_path_params(
    parameter_definitions: tuple[PathParameterDefinition, ...], path_param_values: tuple[str, ...]
) -> dict[str, Any]:
    """Parse path parameters into a dictionary of values.

    Args:
        parameter_definitions: The parameter definitions tuple from the route.
        path_param_values: The string values extracted from the url

    Raises:
        ValueError: If any of path parameters can not be parsed into a value.

    Returns:
        A dictionary of parsed path parameters.
    """
    return {
        param_definition.name: param_definition.parser(value) if param_definition.parser else value
        for param_definition, value in zip(parameter_definitions, path_param_values, strict=False)
    }


def parse_path_to_route(
    method: Method | None,
    mount_paths_regex: Pattern | None,
    mount_routes: dict[str, RouteTrieNode],
    path: str,
    plain_routes: set[str],
    root_node: RouteTrieNode,
) -> tuple[ASGIApp, RouteHandlerType, str, dict[str, Any], str]:
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
        NotFoundException: If no correlating node is found or if path params can not be parsed into values according to the node definition.

    Returns:
        A tuple containing the stack of middlewares and the route handler that is wrapped by it.
    """

    try:
        if path in plain_routes:
            asgi_app, handler = parse_node_handlers(node=root_node.children[path], method=method)
            return asgi_app, handler, path, {}, path

        if mount_paths_regex and (match := mount_paths_regex.match(path)):
            mount_path = path[: match.end()]
            mount_node = mount_routes[mount_path]
            remaining_path = path[match.end() :]
            # since we allow regular handlers under static paths, we must validate that the request does not match
            # any such handler.
            children = (
                normalize_path(sub_route)
                for sub_route in mount_node.children or []
                if sub_route != mount_path and isinstance(sub_route, str)
            )
            if not any(remaining_path.startswith(f"{sub_route}/") for sub_route in children):
                asgi_app, handler = parse_node_handlers(node=mount_node, method=method)
                remaining_path = remaining_path or "/"
                remaining_path = remaining_path if remaining_path.endswith("/") else f"{remaining_path}/"
                return asgi_app, handler, remaining_path, {}, root_node.path_template

        node, path_parameters, path = traverse_route_map(
            root_node=root_node,
            path=path,
        )
        asgi_app, handler = parse_node_handlers(node=node, method=method)
        key = method or ("asgi" if node.is_asgi else "websocket")
        parsed_path_parameters = parse_path_params(node.path_parameters[key], tuple(path_parameters))

        return (
            asgi_app,
            handler,
            path,
            parsed_path_parameters,
            node.path_template,
        )
    except ValueError as e:
        raise NotFoundException() from e
