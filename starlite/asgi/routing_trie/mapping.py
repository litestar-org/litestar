from pathlib import Path
from typing import TYPE_CHECKING, List, Set, Type, Union, cast

from starlette.middleware import Middleware as StarletteMiddleware

from starlite.asgi.routing_trie.types import ASGIHandlerMapping
from starlite.asgi.utils import wrap_in_exception_handler
from starlite.exceptions import ImproperlyConfiguredException
from starlite.types.internal import PathParameterDefinition
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.asgi.routing_trie.types import RouteTrieNode
    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from starlite.types import ASGIApp, RouteHandlerType


def map_route_to_trie(
    app: "Starlite",
    root_node: "RouteTrieNode",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    static_routes: Set[str],
    plain_routes: Set[str],
) -> "RouteTrieNode":
    """Adds a new route path (e.g. '/foo/bar/{param:int}') into the route_map
    tree.

    Inserts non-parameter paths ('plain routes') off the tree's root
    node. For paths containing parameters, splits the path on '/' and
    nests each path segment under the previous segment's node (see
    prefix tree / trie).
    """
    current_node = root_node
    path = route.path

    if route.path_parameters or path in static_routes:
        for component in construct_route_path_components(route_path_components=route.path_components):
            if isinstance(component, PathParameterDefinition):
                current_node["path_param_type"] = component.type
                if component.type is Path:
                    break

                next_node_key: Union[str, Type] = component.type

            else:
                next_node_key = component
                current_node["child_keys"].append(component)

            if next_node_key not in current_node["children"]:
                current_node["children"][next_node_key] = create_node()

            current_node = current_node["children"][next_node_key]
            if current_node["is_static"] and current_node["path_param_type"] is not None:
                raise ImproperlyConfiguredException("Cannot have path parameters configured for a static path.")
    else:
        if path not in root_node["children"]:
            root_node["children"][path] = create_node()
        plain_routes.add(path)
        current_node = root_node["children"][path]

    configure_node(route=route, app=app, node=current_node, static_routes=static_routes)
    return current_node


def construct_route_path_components(
    route_path_components: List[Union[str, "PathParameterDefinition"]]
) -> List[Union[str, "PathParameterDefinition"]]:
    """Takes a list of path components and normalizes it to contain continuous
    sections rather than short segments.

    Examples:
        Given a list ["base", "sub", "path"] returns ["/base/sub/spath"].

    Args:
        route_path_components: A given Route's parsed path components list.

    Returns:
        A normalized path components list.
    """
    path_components: List[Union[str, "PathParameterDefinition"]] = []
    last_continuous_plain_path_segment = ""

    for component in route_path_components:
        if isinstance(component, PathParameterDefinition):

            if last_continuous_plain_path_segment:
                path_components.append(normalize_path(last_continuous_plain_path_segment))
                last_continuous_plain_path_segment = ""

            if component.type is Path:
                path_components.append(component)
                break

            path_components.append(component)

        else:
            last_continuous_plain_path_segment += f"/{component}"

    if last_continuous_plain_path_segment:
        path_components.append(last_continuous_plain_path_segment)

    return path_components


def create_node() -> "RouteTrieNode":
    """Creates a RouteMapNode instance.

    Returns:
        A route map node instance.
    """

    return {
        "asgi_handlers": {},
        "child_keys": [],
        "children": {},
        "is_mount": False,
        "is_static": False,
        "path_param_type": None,
        "path_parameters": [],
    }


def configure_node(
    app: "Starlite",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    node: "RouteTrieNode",
    static_routes: Set[str],
) -> None:
    """Set required attributes and route handlers on route_map tree node."""
    from starlite.routes import HTTPRoute, WebSocketRoute

    node["child_keys"] = sorted(node["child_keys"], reverse=True)

    if not node["path_parameters"]:
        node["path_parameters"] = route.path_parameters

    if route.path in static_routes:
        # if node["children"]:
        #     raise ImproperlyConfiguredException("Cannot have configured routes below a static path")
        node["is_static"] = True

    if isinstance(route, HTTPRoute):
        for method, handler_mapping in route.route_handler_map.items():
            handler, _ = handler_mapping
            node["asgi_handlers"][method] = ASGIHandlerMapping(
                asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=handler),
                handler=handler,
            )

    elif isinstance(route, WebSocketRoute):
        node["asgi_handlers"]["websocket"] = ASGIHandlerMapping(
            asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=route.route_handler),
            handler=route.route_handler,
        )

    else:
        node["asgi_handlers"]["asgi"] = ASGIHandlerMapping(
            asgi_app=build_route_middleware_stack(app=app, route=route, route_handler=route.route_handler),
            handler=route.route_handler,
        )
        node["is_mount"] = True


def build_route_middleware_stack(
    app: "Starlite",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    route_handler: "RouteHandlerType",
) -> "ASGIApp":
    """Constructs a middleware stack that serves as the point of entry for each
    route."""
    from starlite.middleware.csrf import CSRFMiddleware

    # we wrap the route.handle method in the ExceptionHandlerMiddleware
    asgi_handler = wrap_in_exception_handler(
        debug=app.debug, app=route.handle, exception_handlers=route_handler.resolve_exception_handlers()  # type: ignore[arg-type]
    )

    if app.csrf_config:
        asgi_handler = CSRFMiddleware(app=asgi_handler, config=app.csrf_config)

    for middleware in route_handler.resolve_middleware():
        if isinstance(middleware, StarletteMiddleware):
            handler, kwargs = middleware
            asgi_handler = handler(app=asgi_handler, **kwargs)
        else:
            asgi_handler = middleware(app=asgi_handler)  # type: ignore

    # we wrap the entire stack again in ExceptionHandlerMiddleware
    return wrap_in_exception_handler(
        debug=app.debug,
        app=cast("ASGIApp", asgi_handler),
        exception_handlers=route_handler.resolve_exception_handlers(),
    )  # pyright: ignore
