from inspect import Signature, iscoroutinefunction
from typing import Any, Dict, List, Optional, Union, cast

from pydantic import validate_arguments
from pydantic.typing import AnyCallable

from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.base import BaseRouteHandler
from starlite.types import Guard


class ASGIRouteHandler(BaseRouteHandler):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        guards: Optional[List[Guard]] = None,
        opt: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(path=path, guards=guards, opt=opt)

    def __call__(self, fn: AnyCallable) -> "ASGIRouteHandler":
        """
        Replaces a function with itself
        """
        self.fn = fn
        self.validate_handler_function()
        return self

    def validate_handler_function(self) -> None:
        """
        Validates the route handler function once it's set by inspecting its return annotations
        """
        super().validate_handler_function()
        signature = Signature.from_callable(cast(AnyCallable, self.fn))

        if signature.return_annotation is not None:
            raise ImproperlyConfiguredException("ASGI handler functions should return 'None'")
        if any(key not in signature.parameters for key in ["scope", "send", "receive"]):
            raise ImproperlyConfiguredException(
                "ASGI handler functions should define 'scope', 'send' and 'receive' arguments"
            )
        if not iscoroutinefunction(self.fn) and not iscoroutinefunction(self.fn.__call__):  # type: ignore[operator]
            raise ImproperlyConfiguredException("Functions decorated with 'asgi' must be async functions")


asgi = ASGIRouteHandler
