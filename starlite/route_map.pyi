"""
This module contains stubs for the route_map module.

The actual implementation is written in rust and is located in <root>/extensions/route_map
"""

from typing import TYPE_CHECKING, Any, Dict, Sequence

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Scope

    from starlite.routes import BaseRoute

class RouteMap:  # pragma: no cover
    def __init__(self, debug: bool = False):
        """
        Create a new RouteMap
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
        :return: True if the path was removed, False otherwise
        """
    def add_routes(self, routes: Sequence["BaseRoute"]) -> None:
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
