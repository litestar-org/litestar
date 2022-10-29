from typing import TYPE_CHECKING

from starlite.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from starlite.asgi.routing_trie.types import (  # type: ignore[attr-defined]
        RouteTrieNode,
    )


def validate_node(node: "RouteTrieNode") -> None:
    """Recursively traverses the trie from the given node upwards.

    Args:
        node: A trie node.

    Raises:
        ImproperlyConfiguredException

    Returns:
        None
    """
    if node["is_asgi"] and bool(set(node["asgi_handlers"].keys()).difference({"asgi"})):
        raise ImproperlyConfiguredException("ASGI handlers must have a unique path not shared by other route handlers.")

    if node["is_mount"] and node["path_param_type"] is not None:
        raise ImproperlyConfiguredException("Path parameters cannot be configured for a static path.")

    if node["is_mount"] and node["children"]:
        raise ImproperlyConfiguredException("Cannot declare routes for sub paths below an ASGI mount route handler.")

    for child in node["children"].values():
        validate_node(node=child)
