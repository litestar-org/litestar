from copy import copy
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseConfig, Extra, validate_arguments
from pydantic.fields import ModelField, Undefined

from starlite.constants import EXTRA_KEY_REQUIRED, EXTRA_KEY_VALUE_TYPE
from starlite.datastructures.provide import Provide
from starlite.exceptions import ImproperlyConfiguredException
from starlite.types import (
    Dependencies,
    Empty,
    EmptyType,
    ExceptionHandlersMap,
    Guard,
    Middleware,
    ParametersMap,
)
from starlite.utils import AsyncCallable, normalize_path

if TYPE_CHECKING:
    from starlite.connection import ASGIConnection
    from starlite.controller import Controller
    from starlite.router import Router
    from starlite.signature import SignatureModel
    from starlite.types import AnyCallable

T = TypeVar("T", bound="BaseRouteHandler")


class ParameterConfig(BaseConfig):
    extra = Extra.allow


class BaseRouteHandler(Generic[T]):
    __slots__ = (
        "_resolved_dependencies",
        "_resolved_guards",
        "_resolved_layered_parameters",
        "dependencies",
        "exception_handlers",
        "fn",
        "guards",
        "middleware",
        "name",
        "opt",
        "owner",
        "paths",
        "signature_model",
    )

    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        path: Union[Optional[str], Optional[List[str]]] = None,
        *,
        dependencies: Optional[Dependencies] = None,
        exception_handlers: Optional[ExceptionHandlersMap] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Middleware]] = None,
        name: Optional[str] = None,
        opt: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self._resolved_dependencies: Union[Dict[str, Provide], EmptyType] = Empty
        self._resolved_guards: Union[List[Guard], EmptyType] = Empty
        self._resolved_layered_parameters: Union[Dict[str, "ModelField"], EmptyType] = Empty
        self.dependencies = dependencies
        self.exception_handlers = exception_handlers
        self.fn: Optional["AnyCallable"] = None
        self.guards = guards
        self.middleware = middleware
        self.name = name
        self.opt: Dict[str, Any] = opt or {}
        self.owner: Optional[Union["Controller", "Router"]] = None
        self.signature_model: Optional[Type["SignatureModel"]] = None
        self.paths = (
            {normalize_path(p) for p in path}
            if path and isinstance(path, list)
            else {normalize_path(path or "/")}  # type: ignore
        )
        self.opt.update(**kwargs)

    @property
    def dependency_name_set(self) -> Set[str]:
        """The set of all dependency names provided in the handler's ownership
        layers."""
        layered_dependencies = (layer.dependencies or {} for layer in self.ownership_layers)
        return {name for layer in layered_dependencies for name in layer.keys()}

    @property
    def ownership_layers(self) -> List[Union[T, "Controller", "Router"]]:
        """Returns the handler layers from the app down to the route handler.

        app -> ... -> route handler
        """
        layers = []

        cur: Any = self
        while cur:
            layers.append(cur)
            cur = cur.owner

        return list(reversed(layers))

    def resolve_layered_parameters(self) -> Dict[str, "ModelField"]:
        """Returns all parameters declared above the handler, transforming them
        into pydantic ModelField instances."""
        if self._resolved_layered_parameters is Empty:
            self._resolved_layered_parameters = {}
            parameters: ParametersMap = {}
            for layer in self.ownership_layers:
                parameters.update(getattr(layer, "parameters", None) or {})

            for key, parameter in parameters.items():
                is_required = parameter.extra[EXTRA_KEY_REQUIRED]
                value_type = parameter.extra[EXTRA_KEY_VALUE_TYPE]
                if value_type is Undefined:
                    value_type = Any
                default_value = parameter.default if parameter.default is not Undefined else ...
                self._resolved_layered_parameters[key] = ModelField(
                    name=key,
                    type_=value_type,
                    field_info=parameter,
                    default=default_value,
                    model_config=ParameterConfig,
                    class_validators=None,
                    required=is_required,
                )
        return cast("Dict[str, ModelField]", self._resolved_layered_parameters)

    def resolve_guards(self) -> List[Guard]:
        """Returns all guards in the handlers scope, starting from highest to
        current layer."""
        if self._resolved_guards is Empty:
            self._resolved_guards = []
            for layer in self.ownership_layers:
                self._resolved_guards.extend(layer.guards or [])
            self._resolved_guards = cast("List[Guard]", [AsyncCallable(guard) for guard in self._resolved_guards])  # type: ignore[arg-type]
        return cast("List[Guard]", self._resolved_guards)

    def resolve_dependencies(self) -> Dict[str, Provide]:
        """Returns all dependencies correlating to handler function's kwargs
        that exist in the handler's scope."""
        if not self.signature_model:
            raise RuntimeError("resolve_dependencies cannot be called before a signature model has been generated")
        if self._resolved_dependencies is Empty:
            self._resolved_dependencies = {}
            for layer in self.ownership_layers:
                for key, value in (layer.dependencies or {}).items():
                    self._validate_dependency_is_unique(
                        dependencies=self._resolved_dependencies, key=key, provider=value
                    )
                    self._resolved_dependencies[key] = value
        return cast("Dict[str, Provide]", self._resolved_dependencies)

    def resolve_middleware(self) -> List["Middleware"]:
        """Builds the middleware stack for the RouteHandler and returns it.

        The middlewares are added from top to bottom (app -> router ->
        controller -> route handler) and then reversed.
        """
        resolved_middleware = []
        for layer in self.ownership_layers:
            resolved_middleware.extend(layer.middleware or [])
        return list(reversed(resolved_middleware))

    def resolve_exception_handlers(self) -> ExceptionHandlersMap:
        """Resolves the exception_handlers by starting from the route handler
        and moving up.

        This method is memoized so the computation occurs only once.
        """
        resolved_exception_handlers = {}
        for layer in self.ownership_layers:
            resolved_exception_handlers.update(layer.exception_handlers or {})
        return resolved_exception_handlers

    async def authorize_connection(self, connection: "ASGIConnection") -> None:
        """Ensures the connection is authorized by running all the route guards
        in scope."""
        for guard in self.resolve_guards():
            await guard(connection, copy(self))  # type: ignore

    @staticmethod
    def _validate_dependency_is_unique(dependencies: Dict[str, Provide], key: str, provider: Provide) -> None:
        """Validates that a given provider has not been already defined under a
        different key."""
        for dependency_key, value in dependencies.items():
            if provider == value:
                raise ImproperlyConfiguredException(
                    f"Provider for key {key} is already defined under the different key {dependency_key}. "
                    f"If you wish to override a provider, it must have the same key."
                )

    def _validate_handler_function(self) -> None:
        """Validates the route handler function once set by inspecting its
        return annotations."""
        if not self.fn:
            raise ImproperlyConfiguredException("Cannot call _validate_handler_function without first setting self.fn")

    def __str__(self) -> str:
        """
        Returns:
            A unique identifier for the route handler
        """
        target = cast("Any", self.fn)
        if not hasattr(target, "__qualname__"):
            target = type(target)
        return f"{target.__module__}.{target.__qualname__}"
