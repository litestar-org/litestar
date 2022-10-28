from typing import TYPE_CHECKING, Dict, List, Optional, Type, Union

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite.types import ASGIApp, Method, RouteHandlerType
    from starlite.types.internal import PathParameterDefinition

AsgiHandlerNodeMapping = Dict[Union["Method", "Literal['websocket', 'asgi']"], "ASGIHandlerMapping"]


class ASGIHandlerMapping(TypedDict):
    """This class encapsulates a route handler node."""

    asgi_app: "ASGIApp"
    handler: "RouteHandlerType"


class RouteTrieNode(TypedDict):
    """This class represents a radix trie node."""

    asgi_handlers: AsgiHandlerNodeMapping
    child_keys: List[str]
    children: Dict[Union[str, Type], "RouteTrieNode"]  # type: ignore[misc]
    is_asgi: bool
    is_mount: bool
    is_static: bool
    path_param_type: Optional[Type]
    path_parameters: List["PathParameterDefinition"]
