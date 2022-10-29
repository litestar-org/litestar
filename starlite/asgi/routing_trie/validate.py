from typing import TYPE_CHECKING

from starlite.asgi.routing_trie.types import PathParameterSentinel
from starlite.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from starlite.asgi.routing_trie.types import RouteTrieNode


def validate_node(node: "RouteTrieNode") -> None:
    """Recursively traverses the trie from the given node upwards.

    Args:
        node: A trie node.

    Raises:
        ImproperlyConfiguredException

    Returns:
        None
    """
    if node["is_asgi"] and bool(set(node["asgi_handlers"]).difference({"asgi"})):
        raise ImproperlyConfiguredException("ASGI handlers must have a unique path not shared by other route handlers.")

    if node["is_static"] and PathParameterSentinel in node["child_keys"]:
        raise ImproperlyConfiguredException("Path parameters cannot be configured for a static path.")

    for child in node["children"].values():
        validate_node(node=child)
