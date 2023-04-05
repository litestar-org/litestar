from __future__ import annotations

from typing import TYPE_CHECKING

from litestar._openapi.schema_generation import create_schema
from litestar._signature.field import SignatureField
from litestar.constants import RESERVED_KWARGS
from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec.parameter import Parameter
from litestar.openapi.spec.schema import Schema
from litestar.params import DependencyKwarg, ParameterKwarg
from litestar.types import Empty

__all__ = (
    "ParameterCollection",
    "create_parameter",
    "create_parameter_for_handler",
    "create_path_parameter_schema",
    "get_layered_parameter",
    "get_recursive_handler_parameters",
)


if TYPE_CHECKING:
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference
    from litestar.types import Dependencies
    from litestar.types.internal_types import PathParameterDefinition


def create_path_parameter_schema(
    path_parameter: "PathParameterDefinition",
    field: "SignatureField",
    generate_examples: bool,
    schemas: dict[str, Schema],
) -> Schema | Reference:
    """Create a path parameter from the given path_param definition."""
    return create_schema(
        field=SignatureField(
            children=None,
            default_value=field.default_value,
            extra=field.extra,
            field_type=path_parameter.type,
            kwarg_model=field.kwarg_model,
            name=field.name,
        ),
        generate_examples=generate_examples,
        plugins=[],
        schemas=schemas,
    )


class ParameterCollection:
    """Facilitates conditional deduplication of parameters.

    If multiple parameters with the same name are produced for a handler, the condition is ignored if the two
    ``Parameter`` instances are the same (the first is retained and any duplicates are ignored). If the ``Parameter``
    instances are not the same, an exception is raised.
    """

    def __init__(self, route_handler: "BaseRouteHandler") -> None:
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
    signature_field: "SignatureField",
    parameter_name: str,
    path_parameters: tuple["PathParameterDefinition", ...],
    generate_examples: bool,
    schemas: dict[str, "Schema"],
) -> Parameter:
    """Create an OpenAPI Parameter instance."""
    result: Schema | Reference | None = None
    kwargs_model = signature_field.kwarg_model if isinstance(signature_field.kwarg_model, ParameterKwarg) else None

    if any(path_param.name == parameter_name for path_param in path_parameters):
        param_in = ParamType.PATH
        is_required = True
        path_parameter = [p for p in path_parameters if parameter_name in p.name][0]
        result = create_path_parameter_schema(
            field=signature_field, generate_examples=generate_examples, path_parameter=path_parameter, schemas=schemas
        )

    elif kwargs_model and kwargs_model.header:
        parameter_name = kwargs_model.header
        param_in = ParamType.HEADER
        is_required = signature_field.is_required
    elif kwargs_model and kwargs_model.cookie:
        parameter_name = kwargs_model.cookie
        param_in = ParamType.COOKIE
        is_required = signature_field.is_required
    else:
        is_required = signature_field.is_required
        param_in = ParamType.QUERY
        parameter_name = kwargs_model.query if kwargs_model and kwargs_model.query else parameter_name

    if not result:
        result = create_schema(field=signature_field, generate_examples=generate_examples, plugins=[], schemas=schemas)

    schema = result if isinstance(result, Schema) else schemas[result.value]

    return Parameter(
        description=schema.description,
        name=parameter_name,
        param_in=param_in,
        required=is_required,
        schema=result,
    )


def get_recursive_handler_parameters(
    field_name: str,
    signature_field: "SignatureField",
    dependencies: "Dependencies",
    route_handler: "BaseRouteHandler",
    path_parameters: tuple["PathParameterDefinition", ...],
    generate_examples: bool,
    schemas: dict[str, "Schema"],
) -> list[Parameter]:
    """Create and return parameters for a handler.

    If the provided field is not a dependency, a normal parameter is created and returned as a list, otherwise
    `create_parameter_for_handler()` is called to generate parameters for the dependency.
    """

    if field_name not in dependencies:
        return [
            create_parameter(
                generate_examples=generate_examples,
                parameter_name=field_name,
                path_parameters=path_parameters,
                schemas=schemas,
                signature_field=signature_field,
            )
        ]
    dependency_fields = dependencies[field_name].signature_model.fields
    return create_parameter_for_handler(
        route_handler, dependency_fields, path_parameters, generate_examples, schemas=schemas
    )


def get_layered_parameter(
    field_name: str,
    signature_field: "SignatureField",
    layered_parameters: dict[str, "SignatureField"],
    path_parameters: tuple["PathParameterDefinition", ...],
    generate_examples: bool,
    schemas: dict[str, "Schema"],
) -> Parameter:
    """Create a layered parameter for a given signature model field.

    Layer info is extracted from the provided ``layered_parameters`` dict and set as the field's ``field_info`` attribute.
    """
    layer_field = layered_parameters[field_name]

    field = signature_field if signature_field.is_parameter_field else layer_field
    default_value = signature_field.default_value if not signature_field.is_empty else layer_field.default_value
    field_type = signature_field.field_type if signature_field is not Empty else layer_field.field_type  # type: ignore

    parameter_name = field_name
    if isinstance(field.kwarg_model, ParameterKwarg):
        parameter_name = field.kwarg_model.query or field.kwarg_model.header or field.kwarg_model.cookie or field_name

    return create_parameter(
        signature_field=SignatureField.create(
            children=field.children,
            default_value=default_value,
            extra=field.extra,
            field_type=field_type,
            kwarg_model=field.kwarg_model,
            name=field_name,
        ),
        generate_examples=generate_examples,
        parameter_name=parameter_name,
        path_parameters=path_parameters,
        schemas=schemas,
    )


def create_parameter_for_handler(
    route_handler: "BaseRouteHandler",
    handler_fields: dict[str, "SignatureField"],
    path_parameters: tuple["PathParameterDefinition", ...],
    generate_examples: bool,
    schemas: dict[str, "Schema"],
) -> list[Parameter]:
    """Create a list of path/query/header Parameter models for the given PathHandler."""
    parameters = ParameterCollection(route_handler=route_handler)
    dependencies = route_handler.resolve_dependencies()

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

    for field_name, signature_field in unique_handler_fields:
        if isinstance(signature_field.kwarg_model, DependencyKwarg) and field_name not in dependencies:
            # never document explicit dependencies
            continue

        for parameter in get_recursive_handler_parameters(
            dependencies=dependencies,
            field_name=field_name,
            generate_examples=generate_examples,
            path_parameters=path_parameters,
            route_handler=route_handler,
            schemas=schemas,
            signature_field=signature_field,
        ):
            parameters.add(parameter)

    for field_name, signature_field in unique_layered_fields:
        parameters.add(
            create_parameter(
                generate_examples=generate_examples,
                parameter_name=field_name,
                path_parameters=path_parameters,
                schemas=schemas,
                signature_field=signature_field,
            )
        )

    for field_name, signature_field in intersection_fields:
        parameters.add(
            get_layered_parameter(
                field_name=field_name,
                generate_examples=generate_examples,
                layered_parameters=layered_parameters,
                path_parameters=path_parameters,
                schemas=schemas,
                signature_field=signature_field,
            )
        )

    return parameters.list()
