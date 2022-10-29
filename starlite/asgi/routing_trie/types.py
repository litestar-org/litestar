from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Set, Type, Union

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite.types import ASGIApp, Method, RouteHandlerType
    from starlite.types.internal import PathParameterDefinition

AsgiHandlerNodeMapping = Dict[Union["Method", "Literal['websocket', 'asgi']"], "ASGIHandlerTuple"]


class ASGIHandlerTuple(NamedTuple):
    """This class encapsulates a route handler node."""

    asgi_app: "ASGIApp"
    handler: "RouteHandlerType"


class RouteTrieNode(TypedDict):
    """This class represents a radix trie node."""

    asgi_handlers: AsgiHandlerNodeMapping
    child_keys: List[str]
    non_parameter_values: Set[str]
    children: Dict[Union[str, Type], "RouteTrieNode"]  # type: ignore[misc]
    is_asgi: bool
    is_mount: bool
    is_static: bool
    path_param_type: Optional[Type]
    path_parameters: List["PathParameterDefinition"]
    parent: Optional["RouteTrieNode"]  # type: ignore[misc]


def create_node(parent: Optional["RouteTrieNode"]) -> "RouteTrieNode":
    """Creates a RouteMapNode instance.

    Returns:
        A route map node instance.
    """

    return {
        "asgi_handlers": {},
        "child_keys": [],
        "children": {},
        "is_asgi": False,
        "is_mount": False,
        "is_static": False,
        "non_parameter_values": set(),
        "parent": parent,
        "path_param_type": None,
        "path_parameters": [],
    }


__all__ = (
    "ASGIHandlerTuple",
    "AsgiHandlerNodeMapping",
    "RouteTrieNode",
    "create_node",
)
