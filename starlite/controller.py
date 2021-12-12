from typing import TYPE_CHECKING, Dict, List, Optional

from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils import normalize_path

if TYPE_CHECKING:  # pragma: no cover
    from starlite.handlers import RouteHandler
    from starlite.provide import Provide
    from starlite.routing import Router


class Controller:
    __slots__ = ("path", "dependencies", "owner")
    path: str
    dependencies: Optional[Dict[str, "Provide"]]
    owner: "Router"

    def __init__(self, owner: "Router"):
        if not hasattr(self, "path") or not self.path:
            raise ImproperlyConfiguredException("Controller subclasses must set a path attribute")
        self.path = normalize_path(self.path)
        self.owner = owner
        if not hasattr(self, "dependencies"):
            self.dependencies = None
        for route_handler in self.get_route_handlers():
            route_handler.owner = self

    def get_route_handlers(self) -> List["RouteHandler"]:
        """
        Returns a list of route handlers defined on the controller
        """
        from starlite.handlers import (  # pylint: disable=import-outside-toplevel
            RouteHandler,
        )

        return [
            getattr(self, f_name)
            for f_name in dir(self)
            if f_name not in dir(Controller) and isinstance(getattr(self, f_name), RouteHandler)
        ]
