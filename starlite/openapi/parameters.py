from typing import TYPE_CHECKING, Any, Dict, List, cast

from openapi_schema_pydantic.v3.v3_1_0.parameter import Parameter
from pydantic import BaseModel
from pydantic.fields import Undefined

from starlite.constants import EXTRA_KEY_REQUIRED, RESERVED_KWARGS
from starlite.enums import ParamType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.openapi.schema import create_schema

if TYPE_CHECKING:
    from openapi_schema_pydantic.v3.v3_1_0.schema import Schema
    from pydantic.fields import ModelField

    from starlite.handlers import BaseRouteHandler


def create_path_parameter_schema(
    path_parameter: Dict[str, Any], field: "ModelField", generate_examples: bool
) -> "Schema":
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

    def __init__(self, route_handler: "BaseRouteHandler") -> None:
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


def create_parameter(
    model_field: "ModelField", parameter_name: str, path_parameters: List[Dict[str, Any]], generate_examples: bool
) -> Parameter:
    """
    Creates an OpenAPI Parameter instance
    """
    schema = None
    is_required = cast(bool, model_field.required) if model_field.required is not Undefined else False
    extra = model_field.field_info.extra

    if any(path_param["name"] == parameter_name for path_param in path_parameters):
        param_in = ParamType.PATH
        is_required = True
        path_parameter = [p for p in path_parameters if parameter_name in p["name"]][0]
        schema = create_path_parameter_schema(
            path_parameter=path_parameter,
            field=model_field,
            generate_examples=generate_examples,
        )
    elif extra.get(ParamType.HEADER):
        parameter_name = extra[ParamType.HEADER]
        param_in = ParamType.HEADER
        is_required = model_field.field_info.extra[EXTRA_KEY_REQUIRED]
    elif extra.get(ParamType.COOKIE):
        parameter_name = extra[ParamType.COOKIE]
        param_in = ParamType.COOKIE
        is_required = model_field.field_info.extra[EXTRA_KEY_REQUIRED]
    else:
        param_in = ParamType.QUERY
        parameter_name = extra.get(ParamType.QUERY) or parameter_name

    if not schema:
        schema = create_schema(field=model_field, generate_examples=generate_examples)

    return Parameter(
        name=parameter_name,
        param_in=param_in,
        required=is_required,
        param_schema=schema,
        description=schema.description,
    )


def create_parameter_for_handler(
    route_handler: "BaseRouteHandler",
    handler_fields: Dict[str, "ModelField"],
    path_parameters: List[Dict[str, Any]],
    generate_examples: bool,
) -> List[Parameter]:
    """
    Create a list of path/query/header Parameter models for the given PathHandler
    """
    parameters = ParameterCollection(route_handler=route_handler)

    dependencies = route_handler.resolve_dependencies()
    for field_name, model_field in handler_fields.items():
        extra = model_field.field_info.extra
        if extra.get("is_dependency") and field_name not in dependencies:
            # never document explicit dependencies
            continue
        if field_name in dependencies:
            dependency_fields = cast(BaseModel, dependencies[field_name].signature_model).__fields__
            for parameter in create_parameter_for_handler(
                route_handler, dependency_fields, path_parameters, generate_examples
            ):
                parameters.add(parameter)
            continue
        if field_name not in RESERVED_KWARGS:
            parameters.add(
                create_parameter(
                    model_field=model_field,
                    parameter_name=field_name,
                    path_parameters=path_parameters,
                    generate_examples=generate_examples,
                )
            )
    return parameters.list()
