from __future__ import annotations

from typing import TYPE_CHECKING

from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.utils import get_formatted_examples
from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec.parameter import Parameter
from litestar.openapi.spec.reference import Reference
from litestar.openapi.spec.schema import Schema
from litestar.params import ParameterKwarg

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar._openapi.operation import OperationDescription
    from litestar.typing import FieldDefinition

__all__ = ("ParameterFactory",)


class ParameterFactory:
    """Factory for creating the OpenAPI Parameters of an operation."""

    def __init__(self, context: OpenAPIContext, operation: OperationDescription) -> None:
        """Initialize ParameterFactory.

        Args:
            context: The OpenAPI context.
            operation: The operation to create parameters for.
        """
        self.context = context
        self.operation = operation
        self.schema_creator = SchemaCreator.from_openapi_context(
            self.context, prefer_alias=True, signature_namespace=operation.signature_namespace
        )

    def create_parameter(self, field_definition: FieldDefinition, parameter_name: str) -> Parameter:
        """Create an OpenAPI Parameter instance for a field definition.

        Args:
            field_definition: The field definition.
            parameter_name: The name of the parameter.
        """
        kwarg_definition = field_definition.kwarg_definition
        if not isinstance(kwarg_definition, ParameterKwarg):
            raise ImproperlyConfiguredException(f"Field {parameter_name!r} does not declare an HTTP parameter source")

        param_in = kwarg_definition.param_type
        result = self.schema_creator.for_field_definition(field_definition)
        schema = result if isinstance(result, Schema) else self.context.schema_registry.from_reference(result).schema

        description = schema.description
        if description is None and schema.all_of:
            reference = next((s for s in schema.all_of if isinstance(s, Reference)), None)
            if reference is not None:
                description = self.context.schema_registry.from_reference(reference).schema.description

        examples = get_formatted_examples(field_definition, kwarg_definition.examples or [])

        return Parameter(
            description=description,
            name=kwarg_definition.name or parameter_name,
            param_in=param_in,
            required=param_in == ParamType.PATH or field_definition.is_required,
            schema=result,
            examples=examples or None,
        )

    def create_parameters(self) -> list[Parameter]:
        """Create the path, query, header and cookie parameters of the operation."""
        return [
            self.create_parameter(field_definition=field_definition, parameter_name=parameter_name)
            for parameter_name, field_definition in self.operation.parameters
        ]
