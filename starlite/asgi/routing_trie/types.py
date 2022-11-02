from typing import TYPE_CHECKING, Dict, List, NamedTuple, Set, Type, Union

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite.types import ASGIApp, Method, RouteHandlerType
    from starlite.types.internal_types import PathParameterDefinition


class PathParameterSentinel:
    """Sentinel class designating a path parameter."""


class ASGIHandlerTuple(NamedTuple):
    """This class encapsulates a route handler node."""

    asgi_app: "ASGIApp"
    """An ASGI stack, composed of a handler function and layers of middleware that wrap it."""
    handler: "RouteHandlerType"
    """The route handler instance."""


class RouteTrieNode(TypedDict):
    """This class represents a radix trie node."""

    asgi_handlers: Dict[Union["Method", "Literal['websocket', 'asgi']"], "ASGIHandlerTuple"]
    """
    A mapping of ASGI handlers stored on the node.
    """
    child_keys: Set[Union[str, Type[PathParameterSentinel]]]
    """
    A set containing the child keys, same as the children dictionary - but as a set, which offers faster lookup.
    """
    children: Dict[Union[str, Type[PathParameterSentinel]], "RouteTrieNode"]  # type: ignore[misc]
    """
    A dictionary mapping path components or using the PathParameterSentinel class to child nodes.
    """
    is_asgi: bool
    """
    Designate the node as having an `@asgi` type handler.
    """
    is_mount: bool
    """
    Designates the node as a "mount" path, meaning that the handler function will be forwarded all sub paths.
    """
    is_path_type: bool
    """
    Designates the node as expecting a path parameter of type 'Path',
    which means that any sub path under the node is considered to be a path parameter value rather than a url.
    """
    is_static: bool
    """
    Designates the node as a static path node, which means that any sub path under the node is considered to be
    a file path in one of the static directories.
    """
    path_parameters: List["PathParameterDefinition"]
    """
    A list of tuples containing path parameter definitions. This is used for parsing extracted path parameter values.
    """


def create_node() -> "RouteTrieNode":
    """Creates a RouteMapNode instance.

    Returns:
        A route map node instance.
    """

    return {
        "asgi_handlers": {},
        "child_keys": set(),
        "children": {},
        "is_asgi": False,
        "is_mount": False,
        "is_static": False,
        "is_path_type": False,
        "path_parameters": [],
    }
