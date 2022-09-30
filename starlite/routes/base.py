import re
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple, Type, Union
from uuid import UUID

from typing_extensions import TypedDict

from starlite.exceptions import ImproperlyConfiguredException
from starlite.kwargs import KwargsModel
from starlite.signature import get_signature_model
from starlite.utils import join_paths, normalize_path

if TYPE_CHECKING:
    from starlite.enums import ScopeType
    from starlite.handlers.base import BaseRouteHandler
    from starlite.types import Method, Receive, Scope, Send

param_match_regex = re.compile(r"{(.*?)}")
param_type_map = {
    "str": str,
    "int": int,
    "float": float,
    "uuid": UUID,
    "decimal": Decimal,
    "date": date,
    "datetime": datetime,
    "time": time,
    "timedelta": timedelta,
    "path": Path,
}


class PathParameterDefinition(TypedDict):
    name: str
    full: str
    type: Type


class RouteHandlerIndex(TypedDict):
    name: str
    handler: "BaseRouteHandler"


class BaseRoute(ABC):
    __slots__ = (
        "app",
        "handler_names",
        "methods",
        "param_convertors",
        "path",
        "path_format",
        "path_parameters",
        "path_components",
        "scope_type",
    )

    def __init__(
        self,
        *,
        handler_names: List[str],
        path: str,
        scope_type: "ScopeType",
        methods: Optional[List["Method"]] = None,
    ) -> None:
        """This is the base Route class used by Starlite. It's an abstract
        class meant to be extended.

        Args:
            handler_names:
            path:
            scope_type:
            methods:
        """
        self.path, self.path_format, self.path_components = self._parse_path(path)
        self.path_parameters: List[PathParameterDefinition] = [
            component for component in self.path_components if isinstance(component, dict)
        ]
        self.handler_names = handler_names
        self.scope_type = scope_type
        self.methods = set(methods or [])
        if "GET" in self.methods:
            self.methods.add("HEAD")

    @abstractmethod
    async def handle(self, scope: "Scope", receive: "Receive", send: "Send") -> None:  # pragma: no cover
        """The route's ASGI App.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        raise NotImplementedError("Route subclasses must implement handle which serves as the ASGI app entry point")

    def create_handler_kwargs_model(self, route_handler: "BaseRouteHandler") -> KwargsModel:
        """Method to create a KwargsModel for a given route handler."""
        dependencies = route_handler.resolve_dependencies()
        signature_model = get_signature_model(route_handler)

        path_parameters = set()
        for param in self.path_parameters:
            param_name = param["name"]
            if param_name in path_parameters:
                raise ImproperlyConfiguredException(f"Duplicate parameter '{param_name}' detected in '{self.path}'.")
            path_parameters.add(param_name)

        return KwargsModel.create_for_signature_model(
            signature_model=signature_model,
            dependencies=dependencies,
            path_parameters=path_parameters,
            layered_parameters=route_handler.resolve_layered_parameters(),
        )

    @staticmethod
    def _validate_path_parameter(param: str) -> None:
        """Validates that a path parameter adheres to the required format and
        datatypes.

        Raises:
            ImproperlyConfiguredException: If the parameter has an invalid format.
        """
        if len(param.split(":")) != 2:
            raise ImproperlyConfiguredException(
                "Path parameters should be declared with a type using the following pattern: '{parameter_name:type}', e.g. '/my-path/{my_param:int}'"
            )
        param_name, param_type = (p.strip() for p in param.split(":"))
        if not param_name:
            raise ImproperlyConfiguredException("Path parameter names should be of length greater than zero")
        if param_type not in param_type_map:
            raise ImproperlyConfiguredException(
                f"Path parameters should be declared with an allowed type, i.e. one of {','.join(param_type_map.keys())}"
            )

    @classmethod
    def _parse_path(cls, path: str) -> Tuple[str, str, List[Union[str, PathParameterDefinition]]]:
        """Normalizes and parses a path.

        Splits the path into a list of components, parsing any that are path parameters. Also builds the OpenAPI
        compatible path, which does not include the type of the path parameters.

        Returns:
            A 3-tuple of the normalized path, the OpenAPI formatted path, and the list of parsed components.
        """
        path = normalize_path(path)

        parsed_components: List[Union[str, PathParameterDefinition]] = []
        path_format_components = []

        components = [component for component in path.split("/") if component]
        for component in components:
            param_match = param_match_regex.fullmatch(component)
            if param_match:
                param = param_match.group(1)
                cls._validate_path_parameter(param)
                param_name, param_type = (p.strip() for p in param.split(":"))
                parsed_components.append(
                    PathParameterDefinition(name=param_name, type=param_type_map[param_type], full=param)
                )
                path_format_components.append("{" + param_name + "}")
            else:
                parsed_components.append(component)
                path_format_components.append(component)

        path_format = join_paths(path_format_components)

        return path, path_format, parsed_components
