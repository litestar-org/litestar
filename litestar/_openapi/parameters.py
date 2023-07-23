from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from litestar.constants import RESERVED_KWARGS
from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec.parameter import Parameter
from litestar.openapi.spec.schema import Schema
from litestar.params import DependencyKwarg, ParameterKwarg
from litestar.types import Empty

__all__ = ("create_parameter_for_handler",)

from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.di import Provide
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference
    from litestar.types.internal_types import PathParameterDefinition


class ParameterCollection:
    """Facilitates conditional deduplication of parameters.

    If multiple parameters with the same name are produced for a handler, the condition is ignored if the two
    ``Parameter`` instances are the same (the first is retained and any duplicates are ignored). If the ``Parameter``
    instances are not the same, an exception is raised.
    """

    def __init__(self, route_handler: BaseRouteHandler) -> None:
        """Initialize ``ParameterCollection``.

        Args:
            route_handler: Associated route handler
        """
        self.route_handler = route_handler
        self._parameters: dict[str, Parameter] = {}

    def add(self, parameter: Parameter) -> None:
        """Add a ``Parameter`` to the collection.

        If an existing parameter with the same name and type already exists, the
        parameter is ignored.

        If an existing parameter with the same name but different type exists, raises
        ``ImproperlyConfiguredException``.
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

    def list(self) -> list[Parameter]:
        """Return a list of all ``Parameter``'s in the collection."""
        return list(self._parameters.values())


def create_parameter(
    field_definition: FieldDefinition,
    parameter_name: str,
    path_parameters: tuple[PathParameterDefinition, ...],
    schema_creator: SchemaCreator,
) -> Parameter:
    """Create an OpenAPI Parameter instance."""

    result: Schema | Reference | None = None
    kwarg_definition = (
        field_definition.kwarg_definition if isinstance(field_definition.kwarg_definition, ParameterKwarg) else None
    )

    if any(path_param.name == parameter_name for path_param in path_parameters):
        param_in = ParamType.PATH
        is_required = True
        path_parameter = next(p for p in path_parameters if parameter_name in p.name)
        result = schema_creator.for_field_definition(replace(field_definition, annotation=path_parameter.type))
    elif kwarg_definition and kwarg_definition.header:
        parameter_name = kwarg_definition.header
        param_in = ParamType.HEADER
        is_required = field_definition.is_required
    elif kwarg_definition and kwarg_definition.cookie:
        parameter_name = kwarg_definition.cookie
        param_in = ParamType.COOKIE
        is_required = field_definition.is_required
    else:
        is_required = field_definition.is_required
        param_in = ParamType.QUERY
        parameter_name = kwarg_definition.query if kwarg_definition and kwarg_definition.query else parameter_name

    if not result:
        result = schema_creator.for_field_definition(field_definition)

    schema = result if isinstance(result, Schema) else schema_creator.schemas[result.value]

    return Parameter(
        description=schema.description,
        name=parameter_name,
        param_in=param_in,
        required=is_required,
        schema=result,
    )


def get_recursive_handler_parameters(
    field_name: str,
    field_definition: FieldDefinition,
    dependency_providers: dict[str, Provide],
    route_handler: BaseRouteHandler,
    path_parameters: tuple[PathParameterDefinition, ...],
    schema_creator: SchemaCreator,
) -> list[Parameter]:
    """Create and return parameters for a handler.

    If the provided field is not a dependency, a normal parameter is created and returned as a list, otherwise
    `create_parameter_for_handler()` is called to generate parameters for the dependency.
    """

    if field_name not in dependency_providers:
        return [
            create_parameter(
                field_definition=field_definition,
                parameter_name=field_name,
                path_parameters=path_parameters,
                schema_creator=schema_creator,
            )
        ]

    dependency_fields = dependency_providers[field_name].signature_model._fields
    return create_parameter_for_handler(
        route_handler=route_handler,
        handler_fields=dependency_fields,
        path_parameters=path_parameters,
        schema_creator=schema_creator,
    )


def get_layered_parameter(
    field_name: str,
    field_definition: FieldDefinition,
    layered_parameters: dict[str, FieldDefinition],
    path_parameters: tuple[PathParameterDefinition, ...],
    schema_creator: SchemaCreator,
) -> Parameter:
    """Create a layered parameter for a given signature model field.

    Layer info is extracted from the provided ``layered_parameters`` dict and set as the field's ``field_info`` attribute.
    """
    layer_field = layered_parameters[field_name]

    field = field_definition if field_definition.is_parameter_field else layer_field
    default = layer_field.default if field_definition.has_default else field_definition.default
    annotation = field_definition.annotation if field_definition is not Empty else layer_field.annotation

    parameter_name = field_name
    if isinstance(field.kwarg_definition, ParameterKwarg):
        parameter_name = (
            field.kwarg_definition.query or field.kwarg_definition.header or field.kwarg_definition.cookie or field_name
        )

    field_definition = FieldDefinition.from_kwarg(
        inner_types=field.inner_types,
        default=default,
        extra=field.extra,
        annotation=annotation,
        kwarg_definition=field.kwarg_definition,
        name=field_name,
    )
    return create_parameter(
        field_definition=field_definition,
        parameter_name=parameter_name,
        path_parameters=path_parameters,
        schema_creator=schema_creator,
    )


def create_parameter_for_handler(
    route_handler: BaseRouteHandler,
    handler_fields: dict[str, FieldDefinition],
    path_parameters: tuple[PathParameterDefinition, ...],
    schema_creator: SchemaCreator,
) -> list[Parameter]:
    """Create a list of path/query/header Parameter models for the given PathHandler."""
    parameters = ParameterCollection(route_handler=route_handler)
    dependency_providers = route_handler.resolve_dependencies()

    layered_parameters = route_handler.resolve_layered_parameters()

    unique_handler_fields = tuple(
        (k, v) for k, v in handler_fields.items() if k not in RESERVED_KWARGS and k not in layered_parameters
    )
    unique_layered_fields = tuple(
        (k, v) for k, v in layered_parameters.items() if k not in RESERVED_KWARGS and k not in handler_fields
    )
    intersection_fields = tuple(
        (k, v) for k, v in handler_fields.items() if k not in RESERVED_KWARGS and k in layered_parameters
    )

    for field_name, field_definition in unique_handler_fields:
        if isinstance(field_definition.kwarg_definition, DependencyKwarg) and field_name not in dependency_providers:
            # never document explicit dependencies
            continue

        for parameter in get_recursive_handler_parameters(
            field_name=field_name,
            field_definition=field_definition,
            dependency_providers=dependency_providers,
            route_handler=route_handler,
            path_parameters=path_parameters,
            schema_creator=schema_creator,
        ):
            parameters.add(parameter)

    for field_name, field_definition in unique_layered_fields:
        parameters.add(
            create_parameter(
                field_definition=field_definition,
                parameter_name=field_name,
                path_parameters=path_parameters,
                schema_creator=schema_creator,
            )
        )

    for field_name, field_definition in intersection_fields:
        parameters.add(
            get_layered_parameter(
                field_name=field_name,
                field_definition=field_definition,
                layered_parameters=layered_parameters,
                path_parameters=path_parameters,
                schema_creator=schema_creator,
            )
        )

    return parameters.list()
