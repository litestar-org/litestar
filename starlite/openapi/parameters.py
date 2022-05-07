from typing import Any, Dict, List

from openapi_schema_pydantic import Parameter, Schema
from pydantic.fields import ModelField

from starlite.constants import RESERVED_KWARGS
from starlite.handlers import BaseRouteHandler
from starlite.openapi.schema import create_schema


def create_path_parameter_schema(path_parameter: Dict[str, Any], field: ModelField, generate_examples: bool) -> Schema:
    """Create a path parameter from the given path_param definition"""
    field.sub_fields = None
    field.outer_type_ = path_parameter["type"]
    return create_schema(field=field, generate_examples=generate_examples)


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
    parameters: List[Parameter] = []
    ignored_fields = [
        *RESERVED_KWARGS,
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
