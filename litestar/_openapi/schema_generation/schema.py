from __future__ import annotations

from collections import deque
from copy import copy
from dataclasses import MISSING, fields
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum, EnumMeta
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Deque,
    Dict,
    FrozenSet,
    Hashable,
    Iterable,
    List,
    Literal,
    Mapping,
    MutableMapping,
    MutableSequence,
    OrderedDict,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
    get_origin,
)
from uuid import UUID

from msgspec.structs import FieldInfo
from msgspec.structs import fields as msgspec_struct_fields
from typing_extensions import NotRequired, Required, get_args, get_type_hints

from litestar._openapi.schema_generation.constrained_fields import (
    create_date_constrained_field_schema,
    create_numerical_constrained_field_schema,
    create_string_constrained_field_schema,
)
from litestar._openapi.schema_generation.examples import create_examples_for_field
from litestar._openapi.schema_generation.utils import sort_schemas_and_references
from litestar.datastructures import UploadFile
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import Reference
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.schema import Schema, SchemaDataContainer
from litestar.pagination import ClassicPagination, CursorPagination, OffsetPagination
from litestar.params import BodyKwarg, ParameterKwarg
from litestar.serialization import encode_json
from litestar.types import DataclassProtocol, Empty, TypedDictClass
from litestar.typing import FieldDefinition
from litestar.utils.predicates import (
    is_class_and_subclass,
    is_dataclass_class,
    is_optional_union,
    is_pydantic_constrained_field,
    is_struct_class,
    is_typed_dict,
    is_undefined_sentinel,
)
from litestar.utils.typing import get_origin_or_inner_type, make_non_optional_union

if TYPE_CHECKING:
    from msgspec import Struct

    from litestar.plugins import OpenAPISchemaPluginProtocol


KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP: dict[str, str] = {
    "content_encoding": "contentEncoding",
    "default": "default",
    "description": "description",
    "enum": "enum",
    "examples": "examples",
    "external_docs": "externalDocs",
    "format": "format",
    "ge": "minimum",
    "gt": "exclusiveMinimum",
    "le": "maximum",
    "lt": "exclusiveMaximum",
    "max_items": "maxItems",
    "max_length": "maxLength",
    "min_items": "minItems",
    "min_length": "minLength",
    "multiple_of": "multipleOf",
    "pattern": "pattern",
    "title": "title",
}

TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
    Decimal: Schema(type=OpenAPIType.NUMBER),
    DefaultDict: Schema(type=OpenAPIType.OBJECT),
    Deque: Schema(type=OpenAPIType.ARRAY),
    Dict: Schema(type=OpenAPIType.OBJECT),
    FrozenSet: Schema(type=OpenAPIType.ARRAY),
    IPv4Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv4Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv4Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv6Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    IPv6Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    IPv6Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    Iterable: Schema(type=OpenAPIType.ARRAY),
    List: Schema(type=OpenAPIType.ARRAY),
    Mapping: Schema(type=OpenAPIType.OBJECT),
    MutableMapping: Schema(type=OpenAPIType.OBJECT),
    MutableSequence: Schema(type=OpenAPIType.ARRAY),
    None: Schema(type=OpenAPIType.NULL),
    OrderedDict: Schema(type=OpenAPIType.OBJECT),
    Path: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI),
    Pattern: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.REGEX),
    Sequence: Schema(type=OpenAPIType.ARRAY),
    Set: Schema(type=OpenAPIType.ARRAY),
    Tuple: Schema(type=OpenAPIType.ARRAY),
    UUID: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.UUID, description="Any UUID string"),
    bool: Schema(type=OpenAPIType.BOOLEAN),
    bytearray: Schema(type=OpenAPIType.STRING),
    bytes: Schema(type=OpenAPIType.STRING),
    date: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE),
    datetime: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE_TIME),
    deque: Schema(type=OpenAPIType.ARRAY),
    dict: Schema(type=OpenAPIType.OBJECT),
    float: Schema(type=OpenAPIType.NUMBER),
    frozenset: Schema(type=OpenAPIType.ARRAY),
    int: Schema(type=OpenAPIType.INTEGER),
    list: Schema(type=OpenAPIType.ARRAY),
    set: Schema(type=OpenAPIType.ARRAY),
    str: Schema(type=OpenAPIType.STRING),
    time: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
    timedelta: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
    tuple: Schema(type=OpenAPIType.ARRAY),
    UploadFile: Schema(
        type=OpenAPIType.STRING,
        content_media_type="application/octet-stream",
    ),
}


def _get_type_schema_name(value: Any) -> str:
    """Extract the schema name from a data container.

    Args:
        value: A data container

    Returns:
        A string
    """
    return cast("str", getattr(value, "__schema_name__", value.__name__))


def create_enum_schema(annotation: EnumMeta) -> Schema:
    """Create a schema instance for an enum.

    Args:
        annotation: An enum.

    Returns:
        A schema instance.
    """
    enum_values: list[str | int] = [v.value for v in annotation]  # type: ignore
    openapi_type = OpenAPIType.STRING if isinstance(enum_values[0], str) else OpenAPIType.INTEGER
    return Schema(type=openapi_type, enum=enum_values)


def _iter_flat_literal_args(annotation: Any) -> Iterable[Any]:
    """Iterate over the flattened arguments of a Literal.

    Args:
        annotation: An Literal annotation.

    Yields:
        The flattened arguments of the Literal.
    """
    for arg in get_args(annotation):
        if get_origin_or_inner_type(arg) is Literal:
            yield from _iter_flat_literal_args(arg)
        else:
            yield arg.value if isinstance(arg, Enum) else arg


def create_literal_schema(annotation: Any) -> Schema:
    """Create a schema instance for a Literal.

    Args:
        annotation: An Literal annotation.

    Returns:
        A schema instance.
    """
    args = tuple(_iter_flat_literal_args(annotation))
    schema = copy(TYPE_MAP[type(args[0])])
    if len(args) > 1:
        schema.enum = args
    else:
        schema.const = args[0]
    return schema


def create_schema_for_annotation(annotation: Any) -> Schema:
    """Get a schema from the type mapping - if possible.

    Args:
        annotation: A type annotation.

    Returns:
        A schema instance or None.
    """

    if annotation in TYPE_MAP:
        return copy(TYPE_MAP[annotation])

    if isinstance(annotation, EnumMeta):
        return create_enum_schema(annotation)

    return Schema()


class SchemaCreator:
    __slots__ = ("generate_examples", "plugins", "schemas", "prefer_alias", "dto_for")

    def __init__(
        self,
        generate_examples: bool = False,
        plugins: Iterable[OpenAPISchemaPluginProtocol] | None = None,
        schemas: dict[str, Schema] | None = None,
        prefer_alias: bool = True,
    ) -> None:
        """Instantiate a SchemaCreator.

        Args:
            generate_examples: Whether to generate examples if none are given.
            plugins: A list of plugins.
            schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.
            prefer_alias: Whether to prefer the alias name for the schema.
        """
        self.generate_examples = generate_examples
        self.plugins = plugins if plugins is not None else []
        self.schemas = schemas if schemas is not None else {}
        self.prefer_alias = prefer_alias

    @property
    def not_generating_examples(self) -> SchemaCreator:
        """Return a SchemaCreator with generate_examples set to False."""
        if not self.generate_examples:
            return self
        new = copy(self)
        new.generate_examples = False
        return new

    def for_field_definition(self, field_definition: FieldDefinition) -> Schema | Reference:
        """Create a Schema for a given FieldDefinition.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        result: Schema | Reference
        if field_definition.is_optional:
            result = self.for_optional_field(field_definition)
        elif field_definition.is_union:
            result = self.for_union_field(field_definition)
        elif is_struct_class(field_definition.annotation):
            result = self.for_struct_class(field_definition.annotation)
        elif is_dataclass_class(field_definition.annotation):
            result = self.for_dataclass(field_definition.annotation)
        elif is_typed_dict(field_definition.annotation):
            result = self.for_typed_dict(field_definition.annotation)
        elif plugins_for_annotation := [
            plugin for plugin in self.plugins if plugin.is_plugin_supported_type(field_definition.annotation)
        ]:
            result = self.for_plugin(field_definition, plugins_for_annotation[0])
        elif is_pydantic_constrained_field(field_definition.annotation) or (
            isinstance(field_definition.kwarg_definition, (ParameterKwarg, BodyKwarg))
            and field_definition.kwarg_definition.is_constrained
        ):
            result = self.for_constrained_field(field_definition)
        elif field_definition.inner_types and not field_definition.is_generic:
            result = self.for_object_type(field_definition)
        elif field_definition.is_generic and (
            get_origin_or_inner_type(field_definition.annotation)
            in (ClassicPagination, CursorPagination, OffsetPagination)
        ):
            result = self.for_builtin_generics(field_definition)
        else:
            result = create_schema_for_annotation(field_definition.annotation)

        return self.process_schema_result(field_definition, result) if isinstance(result, Schema) else result

    def for_optional_field(self, field_definition: FieldDefinition) -> Schema:
        """Create a Schema for an optional FieldDefinition.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        schema_or_reference = self.for_field_definition(
            FieldDefinition.from_kwarg(
                annotation=make_non_optional_union(field_definition.annotation),
                name=field_definition.name,
                default=field_definition.default,
            )
        )
        if isinstance(schema_or_reference, Schema) and isinstance(schema_or_reference.one_of, list):
            result = schema_or_reference.one_of
        else:
            result = [schema_or_reference]

        return Schema(one_of=[Schema(type=OpenAPIType.NULL), *result])

    def for_union_field(self, field_definition: FieldDefinition) -> Schema:
        """Create a Schema for a union FieldDefinition.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        inner_types = [f for f in (field_definition.inner_types or []) if not is_undefined_sentinel(f.annotation)]
        values = list(map(self.for_field_definition, inner_types))
        return Schema(one_of=sort_schemas_and_references(values))

    def for_object_type(self, field_definition: FieldDefinition) -> Schema:
        """Create schema for object types (dict, Mapping, list, Sequence etc.) types.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        if field_definition.is_mapping:
            return Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=(
                    self.for_field_definition(field_definition.inner_types[1])
                    if field_definition.inner_types and len(field_definition.inner_types) == 2
                    else None
                ),
            )

        if field_definition.is_non_string_sequence or field_definition.is_non_string_iterable:
            items = list(map(self.for_field_definition, field_definition.inner_types or ()))
            return Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(one_of=sort_schemas_and_references(items)) if len(items) > 1 else items[0],
            )

        if field_definition.is_literal:
            return create_literal_schema(field_definition.annotation)

        raise ImproperlyConfiguredException(
            f"Parameter '{field_definition.name}' with type '{field_definition.annotation}' could not be mapped to an Open API type. "
            f"This can occur if a user-defined generic type is resolved as a parameter. If '{field_definition.name}' should "
            "not be documented as a parameter, annotate it using the `Dependency` function, e.g., "
            f"`{field_definition.name}: ... = Dependency(...)`."
        )

    def for_builtin_generics(self, field_definition: FieldDefinition) -> Schema:
        """Handle builtin generic types.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        origin = get_origin_or_inner_type(field_definition.annotation)
        if origin is ClassicPagination:
            return Schema(
                type=OpenAPIType.OBJECT,
                properties={
                    "items": Schema(
                        type=OpenAPIType.ARRAY,
                        items=self.for_field_definition(field_definition.inner_types[0]),
                    ),
                    "page_size": Schema(type=OpenAPIType.INTEGER, description="Number of items per page."),
                    "current_page": Schema(type=OpenAPIType.INTEGER, description="Current page number."),
                    "total_pages": Schema(type=OpenAPIType.INTEGER, description="Total number of pages."),
                },
            )

        if origin is OffsetPagination:
            return Schema(
                type=OpenAPIType.OBJECT,
                properties={
                    "items": Schema(
                        type=OpenAPIType.ARRAY,
                        items=self.for_field_definition(field_definition.inner_types[0]),
                    ),
                    "limit": Schema(type=OpenAPIType.INTEGER, description="Maximal number of items to send."),
                    "offset": Schema(type=OpenAPIType.INTEGER, description="Offset from the beginning of the query."),
                    "total": Schema(type=OpenAPIType.INTEGER, description="Total number of items."),
                },
            )

        cursor_schema = self.not_generating_examples.for_field_definition(field_definition.inner_types[0])
        cursor_schema.description = "Unique ID, designating the last identifier in the given data set. This value can be used to request the 'next' batch of records."

        return Schema(
            type=OpenAPIType.OBJECT,
            properties={
                "items": Schema(
                    type=OpenAPIType.ARRAY,
                    items=self.for_field_definition(field_definition=field_definition.inner_types[1]),
                ),
                "cursor": cursor_schema,
                "results_per_page": Schema(type=OpenAPIType.INTEGER, description="Maximal number of items to send."),
            },
        )

    def for_plugin(self, field_definition: FieldDefinition, plugin: OpenAPISchemaPluginProtocol) -> Schema | Reference:
        """Create a schema using a plugin.

        Args:
            field_definition: A signature field instance.
            plugin: A plugin for the field type.

        Returns:
            A schema instance.
        """
        schema = plugin.to_openapi_schema(field_definition=field_definition, schema_creator=self)
        if isinstance(schema, SchemaDataContainer):
            return self.for_field_definition(
                FieldDefinition.from_kwarg(
                    annotation=schema.data_container,
                    name=field_definition.name,
                    default=field_definition.default,
                    extra=field_definition.extra,
                    kwarg_definition=field_definition.kwarg_definition,
                )
            )
        return schema  # pragma: no cover

    def for_struct_class(self, annotation: type[Struct]) -> Schema:
        """Create a schema object for a given msgspec.Struct class.

        Args:
            annotation: A msgspec.Struct class.

        Returns:
            A schema instance.
        """

        def _is_field_required(field: FieldInfo) -> bool:
            return field.required or field.default_factory is Empty

        return Schema(
            required=sorted(
                [
                    field.encode_name
                    for field in msgspec_struct_fields(annotation)
                    if _is_field_required(field=field) and not is_optional_union(field.type)
                ]
            ),
            properties={
                field.encode_name: self.for_field_definition(FieldDefinition.from_kwarg(field.type, field.encode_name))
                for field in msgspec_struct_fields(annotation)
            },
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(annotation),
        )

    # noinspection PyDataclass
    def for_dataclass(self, annotation: type[DataclassProtocol]) -> Schema:
        """Create a schema object for a given dataclass class.

        Args:
            annotation: A dataclass class.

        Returns:
            A schema instance.
        """
        annotation_hints = get_type_hints(annotation, include_extras=True)
        return Schema(
            required=sorted(
                [
                    field.name
                    for field in fields(annotation)
                    if (
                        field.default is MISSING
                        and field.default_factory is MISSING
                        and not is_optional_union(annotation_hints[field.name])
                    )
                ]
            ),
            properties={
                k: self.for_field_definition(FieldDefinition.from_kwarg(v, k)) for k, v in annotation_hints.items()
            },
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(annotation),
        )

    # noinspection PyTypedDict
    def for_typed_dict(self, annotation: TypedDictClass) -> Schema:
        """Create a schema object for a given typed dict.

        Args:
            annotation: A typed-dict class.

        Returns:
            A schema instance.
        """
        return Schema(
            required=sorted(getattr(annotation, "__required_keys__", [])),
            properties={
                k: self.for_field_definition(FieldDefinition.from_kwarg(v, k))
                for k, v in {
                    k: get_args(v)[0] if get_origin(v) in (Required, NotRequired) else v
                    for k, v in get_type_hints(annotation, include_extras=True).items()
                }.items()
            },
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(annotation),
        )

    def for_constrained_field(self, field: FieldDefinition) -> Schema:
        """Create Schema for Pydantic Constrained fields (created using constr(), conint() and so forth, or by subclassing
        Constrained*)

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        kwarg_definition = cast(Union[ParameterKwarg, BodyKwarg], field.kwarg_definition)
        if any(is_class_and_subclass(field.annotation, t) for t in (int, float, Decimal)):
            return create_numerical_constrained_field_schema(field.annotation, kwarg_definition)
        if any(is_class_and_subclass(field.annotation, t) for t in (str, bytes)):  # type: ignore[arg-type]
            return create_string_constrained_field_schema(field.annotation, kwarg_definition)
        if any(is_class_and_subclass(field.annotation, t) for t in (date, datetime)):
            return create_date_constrained_field_schema(field.annotation, kwarg_definition)
        return self.for_collection_constrained_field(field)

    def for_collection_constrained_field(self, field_definition: FieldDefinition) -> Schema:
        """Create Schema from Constrained List/Set field.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        schema = Schema(type=OpenAPIType.ARRAY)
        kwarg_definition = cast(Union[ParameterKwarg, BodyKwarg], field_definition.kwarg_definition)
        if kwarg_definition.min_items:
            schema.min_items = kwarg_definition.min_items
        if kwarg_definition.max_items:
            schema.max_items = kwarg_definition.max_items
        if any(is_class_and_subclass(field_definition.annotation, t) for t in (set, frozenset)):  # type: ignore[arg-type]
            schema.unique_items = True

        item_creator = self.not_generating_examples
        if field_definition.inner_types:
            items = list(map(item_creator.for_field_definition, field_definition.inner_types))
            if len(items) > 1:
                schema.items = Schema(one_of=sort_schemas_and_references(items))
            else:
                schema.items = items[0]
        else:
            schema.items = item_creator.for_field_definition(
                FieldDefinition.from_kwarg(
                    field_definition.annotation.item_type, f"{field_definition.annotation.__name__}Field"
                )
            )
        return schema

    def process_schema_result(self, field: FieldDefinition, schema: Schema) -> Schema | Reference:
        if field.kwarg_definition and field.is_const and field.has_default and schema.const is None:
            schema.const = field.default

        if field.kwarg_definition:
            for kwarg_definition_key, schema_key in KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
                if (value := getattr(field.kwarg_definition, kwarg_definition_key, Empty)) and (
                    not isinstance(value, Hashable) or not is_undefined_sentinel(value)
                ):
                    setattr(schema, schema_key, value)

        if not schema.examples and self.generate_examples:
            schema.examples = create_examples_for_field(field)

        if schema.title and schema.type in (OpenAPIType.OBJECT, OpenAPIType.ARRAY):
            if schema.title in self.schemas and hash(self.schemas[schema.title]) != hash(schema):
                raise ImproperlyConfiguredException(
                    f"Two different schemas with the title {schema.title} have been defined.\n\n"
                    f"first: {encode_json(self.schemas[schema.title].to_schema()).decode()}\n"
                    f"second: {encode_json(schema.to_schema()).decode()}\n\n"
                    f"To fix this issue, either rename the base classes from which these titles are derived or manually"
                    f"set a 'title' kwarg in the route handler."
                )

            self.schemas[schema.title] = schema
            return Reference(ref=f"#/components/schemas/{schema.title}")
        return schema
