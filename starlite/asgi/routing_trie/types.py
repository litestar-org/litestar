from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Dict,
    KeysView,
    List,
    Literal,
    NamedTuple,
    Optional,
    Type,
    Union,
)

from starlite.types.internal_types import PathParameterDefinition

if TYPE_CHECKING:

    from starlite.types import ASGIApp, Method, RouteHandlerType


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
        "child_path_parameter_type_map",
        "children",
        "is_asgi",
        "is_mount",
        "is_path_type",
        "path",
        "path_parameters",
        "path_type_path_param_definition",
    )

    asgi_handlers: Dict[Union["Method", Literal["websocket", "asgi"]], "ASGIHandlerTuple"]
    """
    A mapping of ASGI handlers stored on the node.
    """
    child_keys: KeysView[Union[str, "PathParameterDefinition"]]
    """
    A set containing the child keys, same as the children dictionary - but as a set, which offers faster lookup.
    """
    child_path_parameter_type_map: Dict[Type, "PathParameterDefinition"]
    """
    Parameter definitions of child nodes mapped to their type.
    """
    children: Dict[Union[str, "PathParameterDefinition"], "RouteTrieNode"]
    """
    A dictionary mapping path components or using the PathParameterSentinel class to child nodes.
    """
    path_type_path_param_definition: Optional["PathParameterDefinition"]
    """
    A path parameter definition of type "path" if one has been registered on the node.
    """
    is_asgi: bool
    """
    Designate the node as having an `@asgi` type handler.
    """
    is_mount: bool
    """
    Designate the node as being a mount route.
    """
    path: str
    """
    String path to this node.
    """
    path_parameters: List["PathParameterDefinition"]
    """
    A list of tuples containing path parameter definitions. This is used for parsing extracted path parameter values.
    """


def create_node(
    parent_node: Optional[RouteTrieNode] = None, component: Optional[Union[str, PathParameterDefinition]] = None
) -> RouteTrieNode:
    """Create a RouteMapNode instance.

    Uses `parent_node` and `component` to construct the `URL` path of the node. If neither provided, path of node is
    `'/'`.

    If `parent_node` and `component` provided, adds the new node to the parent's `children` mapping.

    Args:
        parent_node: The parent of the new node, if not root.
        component: The path component that the node is to represent, or `None` if root.

    Returns:
        A route map node instance.
    """
    parent_path = ("" if parent_node is None else parent_node.path).rstrip("/")
    node_path = f"{{{component.full}}}" if isinstance(component, PathParameterDefinition) else component or ""
    path = "/".join((parent_path, node_path))

    children: Dict[Union[str, "PathParameterDefinition"], "RouteTrieNode"] = {}
    node = RouteTrieNode(
        asgi_handlers={},
        child_keys=children.keys(),
        child_path_parameter_type_map={},
        children=children,
        is_asgi=False,
        is_mount=False,
        path=path,
        path_type_path_param_definition=None,
        path_parameters=[],
    )
    if parent_node is not None and component is not None:
        parent_node.children[component] = node
    return node
