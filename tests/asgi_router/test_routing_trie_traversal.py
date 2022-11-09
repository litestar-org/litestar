from typing import TYPE_CHECKING

import pytest

from starlite.asgi.routing_trie.traversal import parse_scope_to_route
from starlite.exceptions import NotFoundException

if TYPE_CHECKING:
    from starlite.asgi.routing_trie.types import RouteTrieNode


def test_parse_scope_to_route_adds_path_params_to_scope_on_404() -> None:
    """Test that 'path_params' key is added to scope when no route resolved for
    path.
    """
    node: "RouteTrieNode" = {
        "asgi_handlers": {},
        "child_keys": set(),
        "children": {},
        "is_asgi": False,
        "is_mount": False,
        "is_path_type": False,
        "is_static": False,
        "path_parameters": [],
    }
    fake_scope = {"path": "/not-found"}
    with pytest.raises(NotFoundException):
        parse_scope_to_route(node, fake_scope, plain_routes=set())  # type:ignore[arg-type]

    assert "path_params" in fake_scope
