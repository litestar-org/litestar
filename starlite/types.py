from inspect import Signature
from typing import Any, Dict

from starlite.decorators import RouteInfo


class RouteHandler:
    """This is a specific version of 'Callable' that represents the function returned from the route decorator"""

    def __call__(self, *args, **kwargs) -> Any:
        ...  # pragma: no cover

    route_info: RouteInfo
    signature: Signature
    annotations: Dict[str, Any]
