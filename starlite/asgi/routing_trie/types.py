from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Literal, NamedTuple, Set, Tuple, Type, Union

if TYPE_CHECKING:

    from starlite.types import ASGIApp, Method, RouteHandlerType
    from starlite.types.internal_types import PathParameterDefinition


class PathParameterSentinel:
    """Sentinel class designating a path parameter."""


class ASGIHandlerTuple(NamedTuple):
    """Encapsulation of a route handler node."""

    asgi_app: "ASGIApp"
    """An ASGI stack, composed of a handler function and layers of middleware that wrap it."""
    handler: "RouteHandlerType"
    """The route handler instance."""


@dataclass(unsafe_hash=True)
class RouteTrieNode:
    """A radix trie node."""

    __slots__ = (
        "asgi_handlers",
        "child_keys",
        "children",
        "is_asgi",
        "is_mount",
        "is_static",
        "is_path_param_node",
        "is_path_type",
        "path_parameters",
    )

    asgi_handlers: Dict[Union["Method", Literal["websocket", "asgi"]], "ASGIHandlerTuple"]
    """A mapping of ASGI handlers stored on the node."""
    child_keys: Set[Union[str, Type[PathParameterSentinel]]]
    """
    A set containing the child keys, same as the children dictionary - but as a set, which offers faster lookup.
    """
    children: Dict[Union[str, Type[PathParameterSentinel]], "RouteTrieNode"]
    """A dictionary mapping path components or using the PathParameterSentinel class to child nodes."""
    is_path_param_node: bool
    """Designates the node as having a path parameter."""
    is_path_type: bool
    """Designates the node as having a 'path' type path parameter."""
    is_asgi: bool
    """Designate the node as having an `@asgi` type handler."""
    is_mount: bool
    """Designate the node as being a mount route."""
    is_static: bool
    """Designate the node as being a static mount route."""
    path_parameters: Dict[Union["Method", Literal["websocket"], Literal["asgi"]], Tuple["PathParameterDefinition", ...]]
    """A list of tuples containing path parameter definitions.

    This is used for parsing extracted path parameter values.
    """


def create_node() -> RouteTrieNode:
    """Create a RouteMapNode instance.

    Returns:
        A route map node instance.
    """

    return RouteTrieNode(
        asgi_handlers={},
        child_keys=set(),
        children={},
        is_path_param_node=False,
        is_asgi=False,
        is_mount=False,
        is_static=False,
        is_path_type=False,
        path_parameters={},
    )
