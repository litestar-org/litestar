import re
from typing import TYPE_CHECKING, List, Optional, Tuple, Type
from uuid import UUID

from typing_extensions import TypedDict

from starlite.exceptions import ImproperlyConfiguredException
from starlite.kwargs import KwargsModel
from starlite.signature import get_signature_model
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlite.enums import ScopeType
    from starlite.handlers.base import BaseRouteHandler
    from starlite.types import Method


param_match_regex = re.compile(r"{(.*?)}")
param_type_map = {"str": str, "int": int, "float": float, "uuid": UUID}


class PathParameterDefinition(TypedDict):
    name: str
    full: str
    type: Type


class BaseRoute:
    __slots__ = (
        "app",
        "handler_names",
        "methods",
        "param_convertors",
        "path",
        "path_format",
        "path_parameters",
        "scope_type",
    )

    def __init__(
        self,
        *,
        handler_names: List[str],
        path: str,
        scope_type: "ScopeType",
        methods: Optional[List["Method"]] = None,
    ):
        self.path, self.path_format, self.path_parameters = self.parse_path(path)
        self.handler_names = handler_names
        self.scope_type = scope_type
        self.methods = set(methods or [])
        if "GET" in self.methods:
            self.methods.add("HEAD")

    @staticmethod
    def validate_path_parameters(parameters: List[str]) -> None:
        """
        Validates that path parameters adhere to the required format and datatypes

        Raises ImproperlyConfiguredException if any parameter is found with invalid format
        """
        for param in parameters:
            if len(param.split(":")) != 2:
                raise ImproperlyConfiguredException(
                    "Path parameters should be declared with a type using the following pattern: '{parameter_name:type}', e.g. '/my-path/{my_param:int}'"
                )
            param_name, param_type = (p.strip() for p in param.split(":"))
            if len(param_name) == 0:
                raise ImproperlyConfiguredException("Path parameter names should be of length greater than zero")
            if param_type not in param_type_map:
                raise ImproperlyConfiguredException(
                    "Path parameters should be declared with an allowed type, i.e. 'str', 'int', 'float' or 'uuid'"
                )

    @classmethod
    def parse_path(cls, path: str) -> Tuple[str, str, List[PathParameterDefinition]]:
        """
        Normalizes and parses a path
        """
        path = normalize_path(path)
        path_format = path
        path_parameters = []
        identified_params = param_match_regex.findall(path)
        cls.validate_path_parameters(identified_params)
        for param in identified_params:
            param_name, param_type = (p.strip() for p in param.split(":"))
            path_format = path_format.replace(param, param_name)
            path_parameters.append(
                PathParameterDefinition(name=param_name, type=param_type_map[param_type], full=param)
            )
        return path, path_format, path_parameters

    def create_handler_kwargs_model(self, route_handler: "BaseRouteHandler") -> KwargsModel:
        """
        Method to create a KwargsModel for a given route handler
        """
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
