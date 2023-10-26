from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

import msgspec

from litestar._kwargs import KwargsModel
from litestar.exceptions import ImproperlyConfiguredException
from litestar.types.internal_types import PathParameterDefinition
from litestar.utils import join_paths, normalize_path

if TYPE_CHECKING:
    from litestar.enums import ScopeType
    from litestar.handlers.base import BaseRouteHandler
    from litestar.types import Method, Receive, Scope, Send


def _parse_datetime(value: str) -> datetime:
    return msgspec.convert(value, datetime)


def _parse_date(value: str) -> date:
    return msgspec.convert(value, date)


def _parse_time(value: str) -> time:
    return msgspec.convert(value, time)


def _parse_timedelta(value: str) -> timedelta:
    try:
        return msgspec.convert(value, timedelta)
    except msgspec.ValidationError:
        return timedelta(seconds=int(float(value)))


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


parsers_map: dict[Any, Callable[[Any], Any]] = {
    float: float,
    int: int,
    Decimal: Decimal,
    UUID: UUID,
    date: _parse_date,
    datetime: _parse_datetime,
    time: _parse_time,
    timedelta: _parse_timedelta,
}


class BaseRoute(ABC):
    """Base Route class used by Litestar.

    It's an abstract class meant to be extended.
    """

    __slots__ = (
        "app",
        "handler_names",
        "methods",
        "path",
        "path_format",
        "path_parameters",
        "path_components",
        "scope_type",
    )

    def __init__(
        self,
        *,
        handler_names: list[str],
        path: str,
        scope_type: ScopeType,
        methods: list[Method] | None = None,
    ) -> None:
        """Initialize the route.

        Args:
            handler_names: Names of the associated handler functions
            path: Base path of the route
            scope_type: Type of the ASGI scope
            methods: Supported methods
        """
        self.path, self.path_format, self.path_components = self._parse_path(path)
        self.path_parameters: tuple[PathParameterDefinition, ...] = tuple(
            component for component in self.path_components if isinstance(component, PathParameterDefinition)
        )
        self.handler_names = handler_names
        self.scope_type = scope_type
        self.methods = set(methods or [])

    @abstractmethod
    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI App of the route.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        raise NotImplementedError("Route subclasses must implement handle which serves as the ASGI app entry point")

    def create_handler_kwargs_model(self, route_handler: BaseRouteHandler) -> KwargsModel:
        """Create a `KwargsModel` for a given route handler."""

        path_parameters = set()
        for param in self.path_parameters:
            if param.name in path_parameters:
                raise ImproperlyConfiguredException(f"Duplicate parameter '{param.name}' detected in '{self.path}'.")
            path_parameters.add(param.name)

        return KwargsModel.create_for_signature_model(
            signature_model=route_handler.signature_model,
            parsed_signature=route_handler.parsed_fn_signature,
            dependencies=route_handler.resolve_dependencies(),
            path_parameters=path_parameters,
            layered_parameters=route_handler.resolve_layered_parameters(),
        )

    @staticmethod
    def _validate_path_parameter(param: str, path: str) -> None:
        """Validate that a path parameter adheres to the required format and datatypes.

        Raises:
            ImproperlyConfiguredException: If the parameter has an invalid format.
        """
        if len(param.split(":")) != 2:
            raise ImproperlyConfiguredException(
                f"Path parameters should be declared with a type using the following pattern: '{{parameter_name:type}}', e.g. '/my-path/{{my_param:int}}' in path: '{path}'"
            )
        param_name, param_type = (p.strip() for p in param.split(":"))
        if not param_name:
            raise ImproperlyConfiguredException("Path parameter names should be of length greater than zero")
        if param_type not in param_type_map:
            raise ImproperlyConfiguredException(
                f"Path parameters should be declared with an allowed type, i.e. one of {', '.join(param_type_map.keys())} in path: '{path}'"
            )

    @classmethod
    def _parse_path(cls, path: str) -> tuple[str, str, list[str | PathParameterDefinition]]:
        """Normalize and parse a path.

        Splits the path into a list of components, parsing any that are path parameters. Also builds the OpenAPI
        compatible path, which does not include the type of the path parameters.

        Returns:
            A 3-tuple of the normalized path, the OpenAPI formatted path, and the list of parsed components.
        """
        path = normalize_path(path)

        parsed_components: list[str | PathParameterDefinition] = []
        path_format_components = []

        components = [component for component in path.split("/") if component]
        for component in components:
            if param_match := param_match_regex.fullmatch(component):
                param = param_match.group(1)
                cls._validate_path_parameter(param, path)
                param_name, param_type = (p.strip() for p in param.split(":"))
                type_class = param_type_map[param_type]
                parser = parsers_map[type_class] if type_class not in {str, Path} else None
                parsed_components.append(
                    PathParameterDefinition(name=param_name, type=type_class, full=param, parser=parser)
                )
                path_format_components.append("{" + param_name + "}")
            else:
                parsed_components.append(component)
                path_format_components.append(component)

        path_format = join_paths(path_format_components)

        return path, path_format, parsed_components
