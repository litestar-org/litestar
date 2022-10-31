from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlite.asgi.routing_trie.types import RouteTrieNode


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
