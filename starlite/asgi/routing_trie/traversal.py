from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from re import sub
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Set, Tuple
from uuid import UUID

from pydantic.datetime_parse import (
    parse_date,
    parse_datetime,
    parse_duration,
    parse_time,
)

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
    from starlite.types.internal import PathParameterDefinition


parsers_map: Dict[Any, Callable] = {
    str: str,
    float: float,
    int: int,
    Decimal: Decimal,
    UUID: UUID,
    Path: lambda x: Path(sub("//+", "", (x.lstrip("/")))),
    date: parse_date,
    datetime: parse_datetime,
    time: parse_time,
    timedelta: parse_duration,
}


def traverse_route_map(
    current_node: "RouteTrieNode", path: str, scope: "Scope", path_params: List[str]
) -> Tuple["RouteTrieNode", List[str]]:
    """Traverses the application route mapping and retrieves the correct node
    for the request url.

    Args:
        current_node: A trie node.
        path: The request's path.
        scope: The ASGI connection scope.
        path_params: A list of extracted path parameters.

    Raises:
         NotFoundException: if no correlating node is found.

    Returns:
        A tuple containing the target RouteMapNode and a list containing all path parameter values.
    """

    if current_node["is_mount"]:
        if current_node["is_static"]:
            scope["path"] = normalize_path(path + "/")
        return current_node, path_params

    if path in current_node["child_keys"]:
        return traverse_route_map(
            current_node=current_node["children"][path],
            path="",
            scope=scope,
            path_params=path_params,
        )

    has_path_param = current_node["path_param_type"] is not None

    if path in {"/", ""}:
        if has_path_param or not current_node["asgi_handlers"]:
            raise NotFoundException()
        return current_node, path_params

    for child_path in current_node["child_keys"]:
        if path.startswith(child_path):
            return traverse_route_map(
                current_node=current_node["children"][child_path],
                path=path[len(child_path) :],
                scope=scope,
                path_params=path_params,
            )

    if has_path_param:
        if current_node["path_param_type"] is Path:
            path_params.append("/".join(path.split("/")[1:]))
            return current_node, path_params
        component = [p for p in path.split("/") if p][0]

        path_params.append(component)
        path = path[len(f"/{component}") :]

        return traverse_route_map(
            current_node=current_node["children"][current_node["path_param_type"]],  # type: ignore[index]
            path=path,
            scope=scope,
            path_params=path_params,
        )

    raise NotFoundException()


def parse_path_parameters(
    path_parameter_definitions: List["PathParameterDefinition"], request_path_parameter_values: List[str]
) -> Dict[str, Any]:
    """Parses path parameters into their expected types.

    Args:
        path_parameter_definitions: A list of [PathParameterDefinition][starlite.route.base.PathParameterDefinition] instances
        request_path_parameter_values: A list of raw strings sent as path parameters as part of the request

    Raises:
        ValidationException: if path parameter parsing fails

    Returns:
        A dictionary mapping path parameter names to parsed values
    """
    result: Dict[str, Any] = {}

    try:
        for idx, parameter_definition in enumerate(path_parameter_definitions):
            raw_param_value = request_path_parameter_values[idx]
            parser = parsers_map[parameter_definition.type]
            result[parameter_definition.name] = parser(raw_param_value)
        return result
    except (ValueError, TypeError, KeyError) as e:  # pragma: no cover
        raise ValidationException(f"unable to parse path parameters {','.join(request_path_parameter_values)}") from e


def parse_scope_to_route(root_node: "RouteTrieNode", scope: "Scope", plain_routes: Set[str]) -> "ASGIHandlerTuple":
    """Given a scope object, retrieve the asgi_handlers and is_mount boolean
    values from correct trie node."""

    path = scope["path"].strip()
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if path in plain_routes:
        current_node: "RouteTrieNode" = root_node["children"][path]
        scope["path_params"] = {}
    else:
        current_node, path_params = traverse_route_map(current_node=root_node, path=path, scope=scope, path_params=[])
        scope["path_params"] = (
            parse_path_parameters(
                path_parameter_definitions=current_node["path_parameters"],
                request_path_parameter_values=path_params,
            )
            if path_params
            else {}
        )

    try:
        if current_node["is_asgi"]:
            return current_node["asgi_handlers"]["asgi"]
        if scope["type"] == ScopeType.HTTP:
            return current_node["asgi_handlers"][scope["method"]]
        return current_node["asgi_handlers"]["websocket"]
    except KeyError as e:
        raise MethodNotAllowedException() from e
