from __future__ import annotations

from typing import TYPE_CHECKING, cast

from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.utils import get_formatted_examples
from litestar.enums import ParamType
from litestar.openapi.spec.parameter import Parameter
from litestar.openapi.spec.reference import Reference
from litestar.openapi.spec.schema import Schema
from litestar.params import ParameterKwarg, PathParameter
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar.handlers.base import BaseRouteHandler
    from litestar.types.internal_types import PathParameterDefinition

__all__ = ("create_parameters_for_handler",)


def _create_parameter(schema_creator: SchemaCreator, name: str, field_definition: FieldDefinition) -> Parameter:
    kwarg_definition = cast("ParameterKwarg", field_definition.kwarg_definition)
    result = schema_creator.for_field_definition(field_definition)
    schema = result if isinstance(result, Schema) else schema_creator.schema_registry.from_reference(result).schema

    description = schema.description
    if description is None and schema.all_of:
        reference = next((s for s in schema.all_of if isinstance(s, Reference)), None)
        if reference is not None:
            description = schema_creator.schema_registry.from_reference(reference).schema.description

    examples = get_formatted_examples(field_definition, kwarg_definition.examples or [])

    return Parameter(
        description=description,
        name=name,
        param_in=kwarg_definition.param_type,
        required=kwarg_definition.param_type is ParamType.PATH or field_definition.is_required,
        schema=result,
        examples=examples or None,
    )


def create_parameters_for_handler(
    context: OpenAPIContext,
    route_handler: BaseRouteHandler,
    path_parameters: dict[str, PathParameterDefinition],
) -> list[Parameter]:
    """Return the OpenAPI parameters of ``route_handler`` on a route with ``path_parameters``.

    One parameter for each request parameter of the handler, in order, except the body, those
    declared with ``include_in_schema=False`` and path parameters the route does not have;
    followed by one for each of ``path_parameters`` no request parameter declares, typed by the
    route.
    """
    schema_creator = SchemaCreator.from_openapi_context(
        context, prefer_alias=True, signature_namespace=route_handler.signature_namespace
    )
    parameters: list[Parameter] = []
    declared_path_parameters: set[str] = set()
    for definition in route_handler._injection_setup.request_parameter_definitions.values():
        if definition.is_body:
            continue
        if definition.param_type is ParamType.PATH:
            declared_path_parameters.add(definition.name)
            if definition.name not in path_parameters:
                continue
        if cast("ParameterKwarg", definition.field_definition.kwarg_definition).include_in_schema:
            parameters.append(_create_parameter(schema_creator, definition.name, definition.field_definition))

    parameters.extend(
        _create_parameter(
            schema_creator,
            name,
            FieldDefinition.from_kwarg(path_parameter.type, name=name, kwarg_definition=PathParameter(name=name)),
        )
        for name, path_parameter in path_parameters.items()
        if name not in declared_path_parameters
    )
    return parameters
