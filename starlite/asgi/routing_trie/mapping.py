from pathlib import Path
from typing import TYPE_CHECKING, List, Set, Tuple, Type, Union, cast

from starlette.middleware import Middleware as StarletteMiddleware

from starlite.asgi.routing_trie.types import ASGIHandlerTuple, create_node
from starlite.asgi.utils import wrap_in_exception_handler
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

    is_mount = hasattr(route, "route_handler") and getattr(route.route_handler, "is_mount", False)  # type: ignore[union-attr]
    is_plain_route = not (route.path_parameters or is_mount)

    for non_parameter_value, component in construct_route_path_components(
        route_path_components=route.path_components
    ) or [(path, path)]:
        if isinstance(component, PathParameterDefinition):
            current_node["path_param_type"] = component.type
            if component.type is Path:
                break

            next_node_key: Union[str, Type] = component.type

        else:
            next_node_key = component
            current_node["child_keys"].append(component)

            if non_parameter_value:
                current_node["non_parameter_values"].add(non_parameter_value)

        if next_node_key not in current_node["children"]:
            current_node["children"][next_node_key] = create_node(parent=current_node)

        current_node = current_node["children"][next_node_key]

    if is_plain_route:
        plain_routes.add(path)

    configure_node(route=route, app=app, node=current_node)
    return current_node


def construct_route_path_components(
    route_path_components: List[Union[str, "PathParameterDefinition"]]
) -> List[Tuple[str, Union[str, "PathParameterDefinition"]]]:
    """Takes a list of path components and normalizes it to contain continuous
    sections rather than short segments.

    Examples:
        Given a list ["base", "sub", "path"] returns ["/base/sub/spath"].

    Args:
        route_path_components: A given Route's parsed path components list.

    Returns:
        A normalized path components list.
    """
    path_components: List[Tuple[str, Union[str, "PathParameterDefinition"]]] = []
    last_continuous_plain_path_segment = ""
    non_parameter_value = ""

    for component in route_path_components:
        if isinstance(component, PathParameterDefinition):
            if last_continuous_plain_path_segment:
                path_components.append((non_parameter_value, normalize_path(last_continuous_plain_path_segment)))
                last_continuous_plain_path_segment = ""
                non_parameter_value = ""

            path_components.append((non_parameter_value, component))

            if component.type is Path:
                break
        else:
            if not non_parameter_value:
                non_parameter_value = component

            last_continuous_plain_path_segment += f"/{component}"

    if last_continuous_plain_path_segment:
        path_components.append((non_parameter_value, last_continuous_plain_path_segment))

    return path_components


def configure_node(
    app: "Starlite",
    route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
    node: "RouteTrieNode",
) -> None:
    """Set required attributes and route handlers on route_map tree node."""
    from starlite.routes import HTTPRoute, WebSocketRoute

    node["child_keys"] = sorted(node["child_keys"], reverse=True)

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
        node["is_mount"] = route.route_handler.is_mount or route.route_handler.is_static
        node["is_static"] = route.route_handler.is_static


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
