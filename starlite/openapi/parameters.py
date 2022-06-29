from typing import Any, Dict, List, cast

from openapi_schema_pydantic.v3.v3_1_0.parameter import Parameter
from openapi_schema_pydantic.v3.v3_1_0.schema import Schema
from pydantic import BaseModel
from pydantic.fields import ModelField, Undefined

from starlite.constants import RESERVED_KWARGS
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers import BaseRouteHandler
from starlite.openapi.schema import create_schema


def create_path_parameter_schema(path_parameter: Dict[str, Any], field: ModelField, generate_examples: bool) -> Schema:
    """Create a path parameter from the given path_param definition"""
    field.sub_fields = None
    field.outer_type_ = path_parameter["type"]
    return create_schema(field=field, generate_examples=generate_examples)


class ParameterCollection:
    """
    Facilitates conditional deduplication of parameters.

    If multiple parameters with the same name are produced for a handler, the condition is
    ignored if the two `Parameter` instances are the same (the first is retained and any
    duplicates are ignored). If the `Parameter` instances are not the same, an exception
    is raised.
    """

    def __init__(self, route_handler: BaseRouteHandler) -> None:
        self.route_handler = route_handler
        self._parameters: Dict[str, Parameter] = {}

    def add(self, parameter: Parameter) -> None:
        """
        Add a `Parameter` to the collection.

        If an existing parameter with the same name and type already exists, the
        parameter is ignored.

        If an existing parameter with the same name but different type exists, raises
        `ImproperlyConfiguredException`.
        """
        if parameter.name not in self._parameters:
            self._parameters[parameter.name] = parameter
            return
        pre_existing = self._parameters[parameter.name]
        if parameter == pre_existing:
            return
        raise ImproperlyConfiguredException(
            f"OpenAPI schema generation for handler `{self.route_handler}` detected multiple parameters named "
            f"'{parameter.name}' with different types."
        )

    def list(self) -> List[Parameter]:
        """
        Return a list of all `Parameter`'s in the collection.
        """
        return list(self._parameters.values())


def create_parameters(
    route_handler: BaseRouteHandler,
    handler_fields: Dict[str, ModelField],
    path_parameters: List[Dict[str, Any]],
    generate_examples: bool,
) -> List[Parameter]:
    """
    Create a list of path/query/header Parameter models for the given PathHandler
    """
    path_parameter_names = [path_param["name"] for path_param in path_parameters]
    parameters = ParameterCollection(route_handler=route_handler)

    dependencies = route_handler.resolve_dependencies()
    for f_name, field in handler_fields.items():
        extra = field.field_info.extra
        if extra.get("is_dependency") and f_name not in dependencies:
            # never document explicit dependencies
            continue
        if f_name in dependencies:
            dependency_fields = cast(BaseModel, dependencies[f_name].signature_model).__fields__
            for parameter in create_parameters(route_handler, dependency_fields, path_parameters, generate_examples):
                parameters.add(parameter)
            continue
        if f_name not in RESERVED_KWARGS:
            schema = None
            param_in = "query"
            required = cast(bool, field.required) if field.required is not Undefined else False
            extra = field.field_info.extra
            header_key = extra.get("header")
            cookie_key = extra.get("cookie")
            query_key = extra.get("query")
            if f_name in path_parameter_names:
                param_in = "path"
                required = True
                schema = create_path_parameter_schema(
                    path_parameter=[p for p in path_parameters if f_name in p["name"]][0],
                    field=field,
                    generate_examples=generate_examples,
                )
            elif header_key:
                f_name = header_key
                param_in = "header"
                required = field.field_info.extra["required"]
            elif cookie_key:
                f_name = cookie_key
                param_in = "cookie"
                required = field.field_info.extra["required"]
            elif query_key:
                f_name = query_key
                param_in = "query"
                required = cast(bool, field.required) if field.required is not Undefined else False
            if not schema:
                schema = create_schema(field=field, generate_examples=generate_examples)
            parameters.add(
                Parameter(
                    name=f_name,
                    param_in=param_in,
                    required=required,
                    param_schema=schema,
                    description=schema.description,
                )
            )
    return parameters.list()
