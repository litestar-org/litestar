from typing import Any, Callable, Collection, Dict, List, Tuple

from starlite.routes import BaseRoute
from starlette.types import ASGIApp, Scope

class RouteMap:
    def __init__(self):
        pass

    def add_routes(self, routes: Collection[BaseRoute]) -> None:
        """
        Add routes to the map
        """
        pass
       
    def parse_scope_to_route(self, scope: Scope, parse_path_params: Callable[[List[Dict[str, Any]], List[str]], Dict[str, Any]]) -> Tuple[Dict[str, ASGIApp], bool]:
        """
        Given a scope object, retrieve the asgi_handlers and is_asgi values from correct trie node.
        
        Raises NotFoundException if no correlating node is found for the scope's path
        """
        pass

    def traverse_to_dict(self, path: str) -> Dict[str, Any]:
        pass

    def add_static_path(self, path: str) -> None:
        """
        Adds a new static path by path name
        """
        pass

    def is_static_path(self, path: str) -> bool:
        """
        Checks if a given path refers to a static path
        """
        pass

    def remove_static_path(self, path: str) -> bool:
        """
        Removes a path from the static path set
        """
        pass

    def add_plain_route(self, path: str) -> None:
        """
        Adds a new plain route by path name
        """
        pass

    def is_plain_route(self, path: str) -> bool:
        """
        Checks if a given path refers to a plain route
        """
        pass

    def remove_plain_route(self, path: str) -> bool:
        """
        Removes a path from the plain route set
        """
        pass

