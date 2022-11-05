from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Set, Tuple, Type, Union, cast

from starlite.asgi.routing_trie.types import (
    ASGIHandlerTuple,
    PathParameterSentinel,
    create_node,
)
from starlite.asgi.utils import wrap_in_exception_handler
from starlite.types.internal_types import PathParameterDefinition

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.asgi.routing_trie.types import RouteTrieNode
    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from starlite.types import ASGIApp, RouteHandlerType


def add_map_route_to_trie(
    app: "Starlite",
    root_node: "RouteTrieNode",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    plain_routes: Set[str],
) -> "RouteTrieNode":
    """Adds a new route path (e.g. '/foo/bar/{param:int}') into the route_map
    tree.

    Inserts non-parameter paths ('plain routes') off the tree's root
    node. For paths containing parameters, splits the path on '/' and
    nests each path segment under the previous segment's node (see
    prefix tree / trie).

    Args:
        app: The Starlite app instance.
        root_node: The root trie node.
        route: The route that is being added.
        plain_routes: The set of plain routes.

    Returns:
        A RouteTrieNode instance.
    """
    current_node = root_node
    path = route.path

    is_mount = hasattr(route, "route_handler") and getattr(route.route_handler, "is_mount", False)  # type: ignore[union-attr]

    if not (route.path_parameters or is_mount):
        plain_routes.add(path)
        if path not in root_node["children"]:
            current_node["children"][path] = create_node()
        current_node = root_node["children"][path]
    else:
        for component in route.path_components:
            if isinstance(component, PathParameterDefinition):
                if component.type is Path:
                    current_node["is_path_type"] = True
                    break

                next_node_key: Union[Type[PathParameterSentinel], str] = PathParameterSentinel

            else:
                next_node_key = component

            if next_node_key not in current_node["children"]:
                current_node["children"][next_node_key] = create_node()

            current_node["child_keys"] = set(current_node["children"].keys())

            current_node = current_node["children"][next_node_key]

    configure_node(route=route, app=app, node=current_node)
    return current_node


def configure_node(
    app: "Starlite",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    node: "RouteTrieNode",
) -> None:
    """Set required attributes and route handlers on route_map tree node.

    Args:
        app: The Starlite app instance.
        route: The route that is being added.
        node: The trie node being configured.

    Returns:
        None
    """
    from starlite.routes import HTTPRoute, WebSocketRoute

    if not node["path_parameters"]:
        node["path_parameters"] = route.path_parameters

    if isinstance(route, HTTPRoute):
        for method, handler_mapping in route.route_handler_map.items():
            handler, _ = handler_mapping
            node["asgi_handlers"][method] = ASGIHandlerTuple(
                asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=handler),
                handler=handler,
            )

    elif isinstance(route, WebSocketRoute):
        node["asgi_handlers"]["websocket"] = ASGIHandlerTuple(
            asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=route.route_handler),
            handler=route.route_handler,
        )

    else:
        node["asgi_handlers"]["asgi"] = ASGIHandlerTuple(
            asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=route.route_handler),
            handler=route.route_handler,
        )
        node["is_asgi"] = True
        node["is_mount"] = route.route_handler.is_mount
        node["is_static"] = route.route_handler.is_static


def build_route_middleware_stack(
    app: "Starlite",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    route_handler: "RouteHandlerType",
) -> "ASGIApp":
    """Constructs a middleware stack that serves as the point of entry for each
    route.

    Args:
        app: The Starlite app instance.
        route: The route that is being added.
        route_handler: The route handler that is being wrapped.

    Returns:
        An ASGIApp that is composed of a "stack" of middlewares.
    """
    from starlite.middleware.csrf import CSRFMiddleware

    # we wrap the route.handle method in the ExceptionHandlerMiddleware
    asgi_handler = wrap_in_exception_handler(
        debug=app.debug, app=route.handle, exception_handlers=route_handler.resolve_exception_handlers()  # type: ignore[arg-type]
    )

    if app.csrf_config:
        asgi_handler = CSRFMiddleware(app=asgi_handler, config=app.csrf_config)

    for middleware in route_handler.resolve_middleware():
        if hasattr(middleware, "__iter__"):
            handler, kwargs = cast("Tuple[Any, Dict[str, Any]]", middleware)
            asgi_handler = handler(app=asgi_handler, **kwargs)
        else:
            asgi_handler = middleware(app=asgi_handler)  # type: ignore

    # we wrap the entire stack again in ExceptionHandlerMiddleware
    return wrap_in_exception_handler(
        debug=app.debug,
        app=cast("ASGIApp", asgi_handler),
        exception_handlers=route_handler.resolve_exception_handlers(),
    )  # pyright: ignore
