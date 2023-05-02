"""Utilities to facilitate transfer of data from one model to another.

There are two general cases for transferring data:

Data model to transfer model
----------------------------

- producing encoded responses from handler return data
- given the type of the transfer model, and an instance of the data model.
- access attribute values of the data model using ``FieldDefinition.name``
- set values on the transfer model using ``FieldDefinition.serialization_name`` if defined, or ``FieldDefinition.name``.

Validation model to data model
------------------------------

- producing data model from inbound data for handler injection
- given the type of the data model, and an instance of the transfer model.
- access attribute values of the transfer model using ``FieldDefinition.serialization_name`` if defined, or ``FieldDefinition.name``.
- set values on the data model using ``FieldDefinition.name``

"""
from __future__ import annotations

import linecache
from typing import TYPE_CHECKING, TypeVar, cast
from uuid import uuid4

from .types import NestedFieldDefinition

if TYPE_CHECKING:
    from typing import Any, Callable, Literal

    from typing_extensions import TypeAlias

    from litestar.dto.factory._backends.types import FieldDefinitionsType, TransferFieldDefinition

T = TypeVar("T")
DirectionType: TypeAlias = 'Literal["in", "out"]'


def determine_kwarg_name_attr_name(
    field_definition: TransferFieldDefinition | NestedFieldDefinition, direction: DirectionType
) -> tuple[str, str]:
    """Determine name of kwarg for model to be created and name of attribute on source model from which to fetch value.

    Args:
        field_definition: The field definition
        direction: The direction of the transfer.

            - If ``"in"`` then the kwarg is for the data model and so the field name is used.
            - If ``"out"`` then the kwarg is for the transfer model and so the serialization name is used, if defined.

    Returns:
        Tuple of kwarg name, attribute name.
    """
    if direction == "in":
        return field_definition.name, field_definition.serialization_name or field_definition.name
    return field_definition.serialization_name or field_definition.name, field_definition.name


def create_kwarg(field_definition: TransferFieldDefinition, source_instance_name: str, direction: DirectionType) -> str:
    """Create a kwarg string for instantiating a type.

    Args:
        field_definition: The field definition to create a kwarg for.
        source_instance_name: The name of the instance to get the value from.
        direction: The direction of the transfer.

            - If ``"in"`` then the kwarg is for the data model and so the field name is used.
            - If ``"out"`` then the kwarg is for the transfer model and so the serialization name is used, if defined.
    """
    kwarg_name, attr_name = determine_kwarg_name_attr_name(field_definition, direction)
    return f"{kwarg_name}={source_instance_name}.{attr_name}"


def create_transfer_function(
    field_definitions: FieldDefinitionsType, destination_type: type[T], direction: DirectionType
) -> Callable[[Any], T]:
    """Create a function that creates an instance of ``destination_type`` from some other instance.

    Args:
        field_definitions: The field definitions for the type.
        destination_type: The type to create an instance of.
        direction: The direction of the transfer.

            - If ``"in"`` then the transfer is from the transfer model to the data model.
            - If ``"out"`` then the transfer is from the data model to the transfer model.
    """
    globs = {"__builtins__": {}, "destination_type": destination_type}
    fn_args = ["source_instance", "destination_type=destination_type"]

    dest_kwargs = []
    for field_definition in field_definitions.values():
        if isinstance(field_definition, NestedFieldDefinition):
            if direction == "in":
                nested_destination_type = field_definition.nested_type
            else:
                nested_destination_type = field_definition.transfer_model

            nested_transfer_function = create_transfer_function(
                field_definition.nested_field_definitions, nested_destination_type, direction
            )
            name = f"{field_definition.unique_name.replace('.', '_')}_function"
            fn_args.append(f"{name}={name}")
            globs[name] = nested_transfer_function
            kwarg_name, attr_name = determine_kwarg_name_attr_name(field_definition, direction)
            if field_definition.field_definition.parsed_type.is_collection:
                dest_kwargs.append(f"{kwarg_name}=[{name}(item) for item in source_instance.{attr_name}]")
            else:
                dest_kwargs.append(f"{kwarg_name}={name}(source_instance.{attr_name})")
        else:
            dest_kwargs.append(create_kwarg(field_definition, "source_instance", direction))

    fn = create_filename(destination_type, direction)
    lines = [
        f"def transfer({', '.join(fn_args)}):",
        f"  return destination_type({', '.join(dest_kwargs)})",
    ]
    script = "\n".join(lines)
    eval(compile(script, fn, "exec"), globs)
    # adding to linecache allows for debugging in pdb and using `inspect` on the function
    linecache.cache[fn] = (len(script), None, lines, fn)
    return cast("Callable[[Any], T]", globs["transfer"])


def create_filename(destination_type: type[Any], direction: DirectionType) -> str:
    """Create a filename for the generated function."""
    return f"transfer_{destination_type.__name__}_{direction}_{uuid4().hex}.py"
