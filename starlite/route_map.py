# A proxy for a Rust extension class that implements the interface below
# The Rust implementation is located at ./starlite/extensions/rust
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Scope

    from starlite.routes import BaseRoute


class RouteMap:
    def __init__(self, starlite: Any):
        pass

    def add_routes(self, routes: List["BaseRoute"]) -> None:
        """
        Add routes to the map
        """

    def resolve_asgi_app(self, scope: "Scope") -> "ASGIApp":
        """
        Given a scope, retrieves the correct ASGI App for the route
        """

    def traverse_to_dict(self, path: str) -> Dict[str, Any]:
        """
        Given a path, traverses the route map to find the corresponding trie node and returns it as a Dict
        """

    def add_static_path(self, path: str) -> None:
        """
        Adds a new static path by path name
        """

    def is_static_path(self, path: str) -> bool:
        """
        Checks if a given path refers to a static path
        """

    def remove_static_path(self, path: str) -> bool:
        """
        Removes a path from the static path set
        """
