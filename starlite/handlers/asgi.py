from inspect import Signature
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from pydantic import validate_arguments

from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.base import BaseRouteHandler
from starlite.types import ExceptionHandler, Guard
from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable


class ASGIRouteHandler(BaseRouteHandler["ASGIRouteHandler"]):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        opt: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(path=path, guards=guards, opt=opt, exception_handlers=exception_handlers)

    def __call__(self, fn: "AnyCallable") -> "ASGIRouteHandler":
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
        signature = Signature.from_callable(cast("AnyCallable", self.fn))

        if signature.return_annotation is not None:
            raise ImproperlyConfiguredException("ASGI handler functions should return 'None'")
        if any(key not in signature.parameters for key in ["scope", "send", "receive"]):
            raise ImproperlyConfiguredException(
                "ASGI handler functions should define 'scope', 'send' and 'receive' arguments"
            )
        if not is_async_callable(self.fn):
            raise ImproperlyConfiguredException("Functions decorated with 'asgi' must be async functions")


asgi = ASGIRouteHandler
