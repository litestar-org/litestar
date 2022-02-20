from copy import copy
from typing import TYPE_CHECKING, Dict, List, Optional, cast

from typing_extensions import Type

from starlite.handlers import BaseRouteHandler
from starlite.response import Response
from starlite.types import (
    AfterRequestHandler,
    BeforeRequestHandler,
    Guard,
    ResponseHeader,
)
from starlite.utils import normalize_path

if TYPE_CHECKING:  # pragma: no cover
    from starlite.provide import Provide
    from starlite.router import Router


class Controller:
    """
    Starlite Controller. This is the basic 'view' component of Starlite.
    """

    __slots__ = (
        "dependencies",
        "owner",
        "path",
        "tags",
        "response_headers",
        "response_class",
        "guards",
        "before_request",
        "after_request",
    )

    dependencies: Optional[Dict[str, "Provide"]]
    owner: "Router"
    path: str
    tags: Optional[List[str]]
    response_headers: Optional[Dict[str, ResponseHeader]]
    response_class: Optional[Type[Response]]
    guards: Optional[List[Guard]]
    # connection-lifecycle hook handlers
    before_request: Optional[BeforeRequestHandler]
    after_request: Optional[AfterRequestHandler]

    def __init__(self, owner: "Router"):
        for key in [
            "dependencies",
            "response_headers",
            "response_class",
            "guards",
            "before_request",
            "after_request",
        ]:
            if not hasattr(self, key):
                setattr(self, key, None)

        self.path = normalize_path(self.path or "/")
        self.owner = owner

    def get_route_handlers(self) -> List[BaseRouteHandler]:
        """
        Returns a list of route handlers defined on the controller
        """
        route_handlers: List[BaseRouteHandler] = []
        route_handler_fields = [
            f_name
            for f_name in dir(self)
            if f_name not in dir(Controller) and isinstance(getattr(self, f_name), BaseRouteHandler)
        ]
        for f_name in route_handler_fields:
            source_route_handler = cast(BaseRouteHandler, getattr(self, f_name))
            route_handler = copy(source_route_handler)
            route_handler.owner = self
            route_handlers.append(route_handler)
        return route_handlers
