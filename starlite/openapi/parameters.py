from typing import Dict, List
from uuid import UUID

from openapi_schema_pydantic import Parameter
from pydantic.fields import ModelField
from typing_extensions import Type

from starlite.handlers import RouteHandler
from starlite.openapi.constants import TYPE_MAP
from starlite.openapi.schema import create_schema


def create_path_parameter(path_param: str) -> Parameter:
    """Create a path parameter from the given path_param string in the format param_name:type"""
    param_type_map: Dict[str, Type] = {
        "str": str,
        "float": float,
        "int": int,
        "uuid": UUID,
    }
    parameter_name, type_name = tuple(path_param.split(":"))
    assert type_name in param_type_map, f"unsupported path param type {type_name}"
    schema = TYPE_MAP[param_type_map[type_name]]
    return Parameter(name=parameter_name, param_in="path", required=True, param_schema=schema)


def create_parameters(
    route_handler: RouteHandler, handler_fields: Dict[str, ModelField], path_parameters: List[str]
) -> List[Parameter]:
    """
    Create a list of path/query/header Parameter models for the given PathHandler
    """
    parameters: List[Parameter] = []

    ignored_fields = [
        "data",
        "request",
        "headers",
        *[path_param.split(":")[0] for path_param in path_parameters],
        *list(route_handler.resolve_dependencies().keys()),
    ]
    for f_name, field in handler_fields.items():
        if f_name not in ignored_fields:
            extra = field.field_info.extra
            header_key = extra.get("header")
            cookie_key = extra.get("cookie")
            query_key = extra.get("query")
            if header_key:
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
            else:
                param_in = "query"
                required = field.required
            parameters.append(
                Parameter(name=f_name, param_in=param_in, param_schema=create_schema(field), required=required)
            )
    return parameters
