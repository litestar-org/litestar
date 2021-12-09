from typing import Callable, Dict, List, Optional

from starlite.decorators import RouteHandlerFunction
from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils import normalize_path


class Controller:
    path: str
    dependencies: Optional[Dict[str, Callable]] = None

    def __init__(self):
        if not hasattr(self, "path") or not self.path:
            raise ImproperlyConfiguredException("Controller subclasses must set a path attribute")
        self.path = normalize_path(self.path)

    def get_route_handlers(self) -> List[RouteHandlerFunction]:
        """
        Returns a list of route handlers defined on the controller
        """
        return [
            getattr(self, f_name)
            for f_name in dir(self)
            if f_name not in dir(Controller) and hasattr(getattr(self, f_name), "route_info")
        ]
