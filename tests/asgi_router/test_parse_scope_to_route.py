import pytest

from starlite.asgi.routing_trie.traversal import parse_scope_to_route
from starlite.asgi.routing_trie.types import create_node
from starlite.exceptions import NotFoundException
from starlite.testing import RequestFactory


def test_parse_scope_to_route_adds_path_params_to_scope_on_404() -> None:
    """Test that 'path_params' key is added to scope when no route resolved for path."""
    node = create_node()
    request = RequestFactory().get("/not-found")
    with pytest.raises(NotFoundException):
        parse_scope_to_route(node, request.scope, plain_routes=set(), mount_routes={}, mount_paths_regex=None)

    assert "path_params" in request.scope
