from copy import copy
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Type,
    Union,
    cast,
)

from anyio.to_thread import run_sync
from pydantic import validate_arguments
from pydantic.typing import AnyCallable
from starlette.requests import HTTPConnection

from starlite.exceptions import ImproperlyConfiguredException
from starlite.provide import Provide
from starlite.signature import SignatureModel
from starlite.types import ExceptionHandler, Guard, Middleware
from starlite.utils import is_async_callable, normalize_path

if TYPE_CHECKING:  # pragma: no cover
    from starlite.controller import Controller
    from starlite.router import Router


class BaseRouteHandler:
    class empty:
        """Placeholder"""

    __slots__ = (
        "dependencies",
        "exception_handlers",
        "fn",
        "guards",
        "middleware",
        "opt",
        "owner",
        "paths",
        "resolved_dependencies",
        "resolved_dependency_name_set",
        "resolved_exception_handlers",
        "resolved_guards",
        "resolved_middleware",
        "signature_model",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        dependencies: Optional[Dict[str, "Provide"]] = None,
        guards: Optional[List[Guard]] = None,
        opt: Optional[Dict[str, Any]] = None,
        middleware: Optional[List[Middleware]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
    ):
        self.paths: List[str] = (
            [normalize_path(p) for p in path]
            if path and isinstance(path, list)
            else [normalize_path(path or "/")]  # type: ignore
        )
        self.dependencies = dependencies
        self.guards = guards
        self.middleware = middleware
        self.opt: Dict[str, Any] = opt or {}
        self.fn: Optional[AnyCallable] = None
        self.owner: Optional[Union["Controller", "Router"]] = None
        self.signature_model: Optional[Type[SignatureModel]] = None
        self.exception_handlers = exception_handlers
        self.resolved_dependencies: Union[Dict[str, Provide], Type[BaseRouteHandler.empty]] = BaseRouteHandler.empty
        self.resolved_dependency_name_set: Union[Set[str], Type[BaseRouteHandler.empty]] = BaseRouteHandler.empty
        self.resolved_guards: Union[List[Guard], Type[BaseRouteHandler.empty]] = BaseRouteHandler.empty
        self.resolved_middleware: Union[List[Middleware], Type[BaseRouteHandler.empty]] = BaseRouteHandler.empty
        self.resolved_exception_handlers: Union[
            Dict[Union[int, Type[Exception]], ExceptionHandler], Type[BaseRouteHandler.empty]
        ] = BaseRouteHandler.empty

    @property
    def dependency_name_set(self) -> Set[str]:
        """
        The set of all dependency names provided in the handler's ownership layers.

        Intended as a fast to compute set of the names of dependencies provided to the handler, and
        available at the time that the handler's signature model is generated. Full resolution of
        dependencies requires that the signature model is already generated and is performed in
        ``BaseRouteHandler.resolve_dependencies()``.
        """
        if self.resolved_dependency_name_set is BaseRouteHandler.empty:
            layered_dependencies = (layer.dependencies or {} for layer in self.ownership_layers())
            self.resolved_dependency_name_set = {name for layer in layered_dependencies for name in layer.keys()}
        return cast(Set[str], self.resolved_dependency_name_set)

    def ownership_layers(self) -> Generator[Union["BaseRouteHandler", "Controller", "Router"], None, None]:
        """
        Returns all the handler and then all owners up to the app level

        handler -> ... -> App
        """
        cur: Any = self
        while cur:
            value = cur
            cur = cur.owner
            yield value

    def resolve_guards(self) -> List[Guard]:
        """Returns all guards in the handlers scope, starting from highest to current layer"""
        if self.resolved_guards is BaseRouteHandler.empty:
            resolved_guards: List[Guard] = []
            for layer in self.ownership_layers():
                if layer.guards:
                    resolved_guards.extend(layer.guards)
            # we reverse the list to ensure that the highest level guards are called first
            self.resolved_guards = list(reversed(resolved_guards))
        return cast(List[Guard], self.resolved_guards)

    def resolve_dependencies(self) -> Dict[str, Provide]:
        """
        Returns all dependencies correlating to handler function's kwargs that exist in the handler's scope
        """
        if not self.signature_model:
            raise RuntimeError("resolve_dependencies cannot be called before a signature model has been generated")
        if self.resolved_dependencies is BaseRouteHandler.empty:
            dependencies: Dict[str, Provide] = {}
            for layer in self.ownership_layers():
                for key, value in (layer.dependencies or {}).items():
                    if key not in dependencies:
                        self.validate_dependency_is_unique(dependencies=dependencies, key=key, provider=value)
                        dependencies[key] = value
            self.resolved_dependencies = dependencies
        return cast(Dict[str, Provide], self.resolved_dependencies)

    def resolve_middleware(self) -> List[Middleware]:
        """
        Builds the middleware stack for the RouteHandler and returns it.

        The middlewares are added from top to bottom (app -> router -> controller -> route handler) and then reversed.
        """
        if self.resolved_middleware is BaseRouteHandler.empty:
            resolved_middleware = []
            for layer in self.ownership_layers():
                if layer.middleware:
                    resolved_middleware.extend(list(reversed(layer.middleware)))
            self.resolved_middleware = resolved_middleware
        return cast(List[Middleware], self.resolved_middleware)

    def resolve_exception_handlers(self) -> Dict[Union[int, Type[Exception]], ExceptionHandler]:
        """
        Resolves the exception_handlers by starting from the route handler and moving up.

        This method is memoized so the computation occurs only once.
        """
        if self.resolved_exception_handlers is BaseRouteHandler.empty:
            exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler] = {}
            for layer in reversed(list(self.ownership_layers())):
                exception_handlers = {**exception_handlers, **(layer.exception_handlers or {})}
            self.resolved_exception_handlers = exception_handlers
        return cast(Dict[Union[int, Type[Exception]], ExceptionHandler], self.resolved_exception_handlers)

    @staticmethod
    def validate_dependency_is_unique(dependencies: Dict[str, Provide], key: str, provider: Provide) -> None:
        """
        Validates that a given provider has not been already defined under a different key
        """
        for dependency_key, value in dependencies.items():
            if provider == value:
                raise ImproperlyConfiguredException(
                    f"Provider for key {key} is already defined under the different key {dependency_key}. "
                    f"If you wish to override a provider, it must have the same key."
                )

    def validate_handler_function(self) -> None:
        """
        Validates the route handler function once it's set by inspecting its return annotations
        """
        if not self.fn:
            raise ImproperlyConfiguredException("Cannot call validate_handler_function without first setting self.fn")

    async def authorize_connection(self, connection: HTTPConnection) -> None:
        """
        Ensures the connection is authorized by running all the route guards in scope
        """
        for guard in self.resolve_guards():
            if is_async_callable(guard):
                await guard(connection, copy(self))  # type: ignore[misc]
            else:
                await run_sync(guard, connection, copy(self))
