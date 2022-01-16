from typing import Any, Dict, List
from uuid import UUID

from openapi_schema_pydantic import Parameter, Schema
from pydantic.fields import ModelField
from typing_extensions import Type

from starlite.handlers import BaseRouteHandler
from starlite.openapi.schema import create_schema


def create_path_parameter_schema(path_parameter: str, field: ModelField, generate_examples: bool) -> Schema:
    """Create a path parameter from the given path_param string in the format param_name:type"""
    param_type_map: Dict[str, Type[Any]] = {
        "str": str,
        "float": float,
        "int": int,
        "uuid": UUID,
    }
    parameter_type = path_parameter.split(":")[1]
    if parameter_type not in param_type_map:
        raise TypeError(f"Unsupported path param type {parameter_type}")
    field.sub_fields = None
    field.outer_type_ = param_type_map[parameter_type]
    return create_schema(field=field, generate_examples=generate_examples)


def create_parameters(
    route_handler: BaseRouteHandler,
    handler_fields: Dict[str, ModelField],
    path_parameters: List[str],
    generate_examples: bool,
) -> List[Parameter]:
    """
    Create a list of path/query/header Parameter models for the given PathHandler
    """
    path_parameter_names = [path_param.split(":")[0] for path_param in path_parameters]
    parameters: List[Parameter] = []
    ignored_fields = [
        "data",
        "request",
        "headers",
        *list(route_handler.resolve_dependencies().keys()),
    ]
    for f_name, field in handler_fields.items():
        if f_name not in ignored_fields:
            schema = None
            param_in = "query"
            required = field.required
            extra = field.field_info.extra
            header_key = extra.get("header")
            cookie_key = extra.get("cookie")
            query_key = extra.get("query")
            if f_name in path_parameter_names:
                param_in = "path"
                required = True
                schema = create_path_parameter_schema(
                    path_parameter=[p for p in path_parameters if f_name in p][0],
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
                required = field.required
            if not schema:
                schema = create_schema(field=field, generate_examples=generate_examples)
            parameters.append(
                Parameter(
                    name=f_name,
                    param_in=param_in,
                    required=required,
                    param_schema=schema,
                    description=schema.description,
                )
            )
    return parameters
