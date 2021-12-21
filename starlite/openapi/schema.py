from dataclasses import is_dataclass
from enum import EnumMeta
from typing import List, Optional, Type, Union

from openapi_schema_pydantic import Schema
from openapi_schema_pydantic.util import PydanticSchema
from pydantic import (
    ConstrainedBytes,
    ConstrainedDecimal,
    ConstrainedFloat,
    ConstrainedInt,
    ConstrainedList,
    ConstrainedSet,
    ConstrainedStr,
)
from pydantic.fields import ModelField
from pydantic_factories import ModelFactory
from pydantic_factories.utils import is_optional, is_pydantic_model, is_union

from starlite.openapi.constants import PYDANTIC_FIELD_SHAPE_MAP, TYPE_MAP
from starlite.openapi.enums import OpenAPIType
from starlite.utils.model import create_parsed_model_field, handle_dataclass


def create_numerical_constrained_field_schema(
    field_type: Union[Type[ConstrainedFloat], Type[ConstrainedInt], Type[ConstrainedDecimal]]
) -> Schema:
    """
    Create Schema from Constrained Int/Float/Decimal field
    """
    schema = Schema(type=OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER)
    if field_type.le is not None:
        schema.maximum = field_type.le
    if field_type.lt is not None:
        schema.exclusiveMaximum = field_type.lt
    if field_type.ge is not None:
        schema.minimum = field_type.ge
    if field_type.gt is not None:
        schema.exclusiveMinimum = field_type.gt
    if field_type.multiple_of is not None:
        schema.multipleOf = field_type.multiple_of
    return schema


def create_string_constrained_field_schema(field_type: Union[Type[ConstrainedStr], Type[ConstrainedBytes]]) -> Schema:
    """
    Create Schema from Constrained Str/Bytes field
    """
    schema = Schema(type=OpenAPIType.STRING)
    if field_type.min_length:
        schema.minLength = field_type.min_length
    if field_type.max_length:
        schema.maxLength = field_type.max_length
    if hasattr(field_type, "regex") and field_type.regex:
        schema.pattern = field_type.regex
    if field_type.to_lower:
        schema.description = "must be in lower case"
    return schema


def create_collection_constrained_field_schema(
    field_type: Union[Type[ConstrainedList], Type[ConstrainedSet]],
    sub_fields: Optional[List[ModelField]],
) -> Schema:
    """
    Create Schema from Constrained List/Set field
    """
    schema = Schema(type=OpenAPIType.ARRAY)
    if field_type.min_items:
        schema.minItems = field_type.min_items
    if field_type.max_items:
        schema.maxItems = field_type.max_items
    if issubclass(field_type, ConstrainedSet):
        schema.uniqueItems = True
    if sub_fields:
        schema.items = [create_schema(sub_field) for sub_field in sub_fields]
    else:
        parsed_model_field = create_parsed_model_field(field_type.item_type)
        schema.items = create_schema(parsed_model_field)
    return schema


def create_constrained_field_schema(
    field_type: Union[
        Type[ConstrainedSet],
        Type[ConstrainedList],
        Type[ConstrainedStr],
        Type[ConstrainedBytes],
        Type[ConstrainedFloat],
        Type[ConstrainedInt],
        Type[ConstrainedDecimal],
    ],
    sub_fields: Optional[List[ModelField]],
) -> Schema:
    """
    Create Schema for Pydantic Constrained fields (created using constr(), conint() etc.) or by subclassing
    """
    if issubclass(field_type, (ConstrainedFloat, ConstrainedInt, ConstrainedDecimal)):
        return create_numerical_constrained_field_schema(field_type=field_type)
    if issubclass(field_type, (ConstrainedStr, ConstrainedBytes)):
        return create_string_constrained_field_schema(field_type=field_type)
    return create_collection_constrained_field_schema(field_type=field_type, sub_fields=sub_fields)


def create_schema(field: ModelField, ignore_optional: bool = False) -> Schema:
    """
    Create a Schema model for a given ModelField
    """
    if is_optional(field) and not ignore_optional:
        return Schema(oneOf=[Schema(type=OpenAPIType.NULL), create_schema(field, ignore_optional=True)])
    if is_pydantic_model(field.outer_type_):
        return PydanticSchema(schema_class=field.outer_type_)
    if is_dataclass(field.outer_type_):
        return PydanticSchema(schema_class=handle_dataclass(field.outer_type_))
    if is_union(field):
        return Schema(oneOf=[create_schema(sub_field) for sub_field in field.sub_fields or []])
    field_type = field.outer_type_
    if field_type in TYPE_MAP:
        return TYPE_MAP[field_type]
    if ModelFactory.is_constrained_field(field_type):
        return create_constrained_field_schema(field_type=field_type, sub_fields=field.sub_fields)
    if isinstance(field_type, EnumMeta):
        enum_values: List[Union[str, int]] = [v.value for v in field_type]  # type: ignore
        openapi_type = OpenAPIType.STRING if isinstance(enum_values[0], str) else OpenAPIType.INTEGER
        return Schema(type=openapi_type, enum=enum_values)
    if field.sub_fields:
        # we are dealing with complex types in this case
        # the problem here is that the Python typing system is too crude to define OpenAPI objects properly
        openapi_type = PYDANTIC_FIELD_SHAPE_MAP[field.shape]
        schema = Schema(type=openapi_type)
        if openapi_type == OpenAPIType.ARRAY:
            schema.items = [create_schema(sub_field) for sub_field in field.sub_fields]
        return schema
    return Schema()
