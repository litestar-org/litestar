# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import dataclasses
from collections import OrderedDict, defaultdict, deque
from collections.abc import Hashable, Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from copy import copy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path
from re import Pattern
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Self,
    cast,
    get_args,
)
from uuid import UUID

from litestar._openapi.datastructures import SchemaRegistry, _get_component_key_override
from litestar._openapi.schema_generation.constrained_fields import (
    create_numerical_constrained_field_schema,
    create_string_constrained_field_schema,
)
from litestar._openapi.schema_generation.unions import _get_shape
from litestar._openapi.schema_generation.utils import (
    _should_create_literal_schema,
    get_json_schema_formatted_examples,
)
from litestar._openapi.utils import is_recursive_type_alias, is_type_alias, resolve_type_alias
from litestar.datastructures import SecretBytes, SecretString, UploadFile
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.reference import Reference
from litestar.openapi.spec.schema import Schema, SchemaDataContainer
from litestar.params import BodyKwarg, KwargDefinition
from litestar.plugins import OpenAPISchemaPlugin
from litestar.types import Empty
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition
from litestar.utils.helpers import get_name
from litestar.utils.predicates import (
    is_class_and_subclass,
    is_undefined_sentinel,
)
from litestar.utils.typing import (
    get_origin_or_inner_type,
    make_non_optional_union,
    unwrap_annotation,
    unwrap_new_type,
)

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar.openapi.spec import Example

KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP: dict[str, str] = {
    "content_encoding": "content_encoding",
    "description": "description",
    "enum": "enum",
    "examples": "examples",
    "external_docs": "external_docs",
    "format": "format",
    "ge": "minimum",
    "gt": "exclusive_minimum",
    "le": "maximum",
    "lt": "exclusive_maximum",
    "max_items": "max_items",
    "max_length": "max_length",
    "min_items": "min_items",
    "min_length": "min_length",
    "multiple_of": "multiple_of",
    "pattern": "pattern",
    "title": "title",
    "read_only": "read_only",
}

_NUMERIC_BOUND_PROPERTIES = frozenset({"minimum", "exclusive_minimum", "maximum", "exclusive_maximum", "multiple_of"})
_NUMERIC_TYPES = frozenset({OpenAPIType.INTEGER, OpenAPIType.NUMBER})
_DATE_BOUND_DESCRIPTIONS = {"gt": "after", "ge": "on or after", "lt": "before", "le": "on or before"}
_DECIMAL_PATTERN = r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"
_LENGTH_PROPERTIES: dict[OpenAPIType, tuple[str, str]] = {
    OpenAPIType.STRING: ("min_length", "max_length"),
    OpenAPIType.ARRAY: ("min_items", "max_items"),
    OpenAPIType.OBJECT: ("min_properties", "max_properties"),
}
_LENGTH_BOUND_INDEX: dict[str, int] = {"min_items": 0, "min_length": 0, "max_items": 1, "max_length": 1}


def _is_empty_tuple(field_definition: FieldDefinition) -> bool:
    return field_definition.origin is tuple and getattr(field_definition.annotation, "__args__", None) == ()


def _get_schema_types(schema: Schema) -> frozenset[OpenAPIType] | None:
    shape = _get_shape(schema, {})
    return None if shape is None else shape[0]


def _get_length_property(kwarg_definition_key: str, schema: Schema) -> str | None:
    if schema.properties is not None:
        return None
    schema_key = KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP[kwarg_definition_key]
    schema_types = _get_schema_types(schema)
    if schema_types is None:
        return schema_key
    sized_types = [sized_type for sized_type in _LENGTH_PROPERTIES if sized_type in schema_types]
    if len(sized_types) != 1:
        return schema_key
    return _LENGTH_PROPERTIES[sized_types[0]][_LENGTH_BOUND_INDEX[kwarg_definition_key]]


def _is_numeric_bound(value: Any, schema: Schema) -> bool:
    if not isinstance(value, (int, float, Decimal)) or isinstance(value, bool):
        return False
    schema_types = _get_schema_types(schema)
    return schema_types is None or not schema_types.isdisjoint(_NUMERIC_TYPES)


def _describe_date_bounds(kwarg_definition: Any) -> str | None:
    bounds = [
        f"{text} {value.isoformat()}"
        for key, text in _DATE_BOUND_DESCRIPTIONS.items()
        if isinstance(value := getattr(kwarg_definition, key, None), date)
    ]
    return f"must be {' and '.join(bounds)}" if bounds else None


TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
    Decimal: Schema(type=OpenAPIType.STRING),
    defaultdict: Schema(type=OpenAPIType.OBJECT),
    deque: Schema(type=OpenAPIType.ARRAY),
    dict: Schema(type=OpenAPIType.OBJECT),
    frozenset: Schema(type=OpenAPIType.ARRAY),
    IPv4Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv4Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4_CIDR),
    IPv4Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4_CIDR),
    IPv6Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    IPv6Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6_CIDR),
    IPv6Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6_CIDR),
    Iterable: Schema(type=OpenAPIType.ARRAY),
    list: Schema(type=OpenAPIType.ARRAY),
    Mapping: Schema(type=OpenAPIType.OBJECT),
    MutableMapping: Schema(type=OpenAPIType.OBJECT),
    MutableSequence: Schema(type=OpenAPIType.ARRAY),
    None: Schema(type=OpenAPIType.NULL),
    NoneType: Schema(type=OpenAPIType.NULL),
    OrderedDict: Schema(type=OpenAPIType.OBJECT),
    Path: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI),
    Pattern: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.REGEX),
    SecretBytes: Schema(type=OpenAPIType.STRING),
    SecretString: Schema(type=OpenAPIType.STRING),
    Sequence: Schema(type=OpenAPIType.ARRAY),
    set: Schema(type=OpenAPIType.ARRAY),
    tuple: Schema(type=OpenAPIType.ARRAY),
    UUID: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.UUID),
    bool: Schema(type=OpenAPIType.BOOLEAN),
    bytearray: Schema(type=OpenAPIType.STRING),
    bytes: Schema(type=OpenAPIType.STRING),
    date: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE),
    datetime: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE_TIME),
    float: Schema(type=OpenAPIType.NUMBER),
    int: Schema(type=OpenAPIType.INTEGER),
    str: Schema(type=OpenAPIType.STRING),
    time: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.TIME),
    timedelta: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
}


def _types_in_list(lst: list[Any]) -> list[OpenAPIType] | OpenAPIType:
    """Extract unique OpenAPITypes present in the values of a list.

    Args:
        lst: A list of values

    Returns:
        OpenAPIType in the given list. If more then one exists, return
        a list of OpenAPITypes.
    """
    schema_types: list[OpenAPIType] = []
    for item in lst:
        schema_type = TYPE_MAP[type(item)].type
        if isinstance(schema_type, OpenAPIType):
            schema_types.append(schema_type)
        else:
            raise RuntimeError("Unexpected type for schema item")  # pragma: no cover

    # Ensure our schema types are sorted alphabetically for any downstream usage sensitive to order changes.
    schema_types = sorted(set(schema_types))
    return schema_types[0] if len(schema_types) == 1 else schema_types


def _get_type_schema_name(field_definition: FieldDefinition) -> str:
    """Extract the schema name from a data container.

    Args:
        field_definition: A field definition instance.

    Returns:
        A string
    """

    if name := getattr(field_definition.annotation, "__schema_name__", None):
        return cast("str", name)

    name = get_name(field_definition.annotation)
    if field_definition.inner_types:
        inner_parts = ", ".join(_get_type_schema_name(t) for t in field_definition.inner_types)
        return f"{name}[{inner_parts}]"

    return name


def _iter_flat_literal_args(annotation: Any) -> Iterable[Any]:
    """Iterate over the flattened arguments of a Literal.

    Args:
        annotation: An Literal annotation.

    Yields:
        The flattened arguments of the Literal.
    """
    # Strip ``Annotated[...]`` (and similar wrappers) so we never iterate over
    # PEP 593 metadata as if it were a literal value. Reachable e.g. via
    # ``Optional[Annotated[Literal[...], Meta(...)]]`` because
    # ``make_non_optional_union`` preserves the ``Annotated`` wrapper.
    annotation, _, _ = unwrap_annotation(annotation)
    for arg in get_args(annotation):
        if get_origin_or_inner_type(arg) is Literal:
            yield from _iter_flat_literal_args(arg)
        else:
            yield arg.value if isinstance(arg, Enum) else arg


def create_literal_schema(annotation: Any, include_null: bool = False) -> Schema:
    """Create a schema instance for a Literal.

    Args:
        annotation: An Literal annotation.
        include_null: Whether to include null as a possible value.

    Returns:
        A schema instance.
    """
    args = list(_iter_flat_literal_args(annotation))
    if include_null and None not in args:
        args.append(None)
    schema = Schema(type=_types_in_list(args))
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

    if annotation is Decimal:
        return Schema(
            one_of=[Schema(type=OpenAPIType.NUMBER), Schema(type=OpenAPIType.STRING, pattern=_DECIMAL_PATTERN)]
        )
    return copy(TYPE_MAP[annotation]) if annotation in TYPE_MAP else Schema()


def _merge_kwarg_definitions(base: KwargDefinition | None, override: KwargDefinition | None) -> KwargDefinition | None:
    if base is None or override is None:
        return override or base
    return dataclasses.replace(
        override,
        **{
            field.name: value
            for field in dataclasses.fields(KwargDefinition)
            if getattr(override, field.name) is None and (value := getattr(base, field.name)) is not None
        },
    )


class SchemaCreator:
    __slots__ = (
        "generate_component_examples",
        "generate_examples",
        "plugins",
        "prefer_alias",
        "schema_registry",
        "signature_namespace",
    )

    def __init__(
        self,
        generate_examples: bool = False,
        plugins: Iterable[OpenAPISchemaPlugin] | None = None,
        prefer_alias: bool = True,
        schema_registry: SchemaRegistry | None = None,
        signature_namespace: dict[str, Any] | None = None,
        generate_component_examples: bool | None = None,
    ) -> None:
        """Instantiate a SchemaCreator.

        Args:
            generate_examples: Whether to generate examples if none are given.
            generate_component_examples: Whether to generate examples for component schemas, which are shared by
                all their usages. Defaults to ``generate_examples``.
            plugins: A list of plugins.
            prefer_alias: Whether to prefer the alias name for the schema.
            schema_registry: A SchemaRegistry instance.
            signature_namespace: Additional names for forward reference resolution.
        """
        self.generate_examples = generate_examples
        self.generate_component_examples = (
            generate_examples if generate_component_examples is None else generate_component_examples
        )
        self.plugins = plugins if plugins is not None else []
        self.prefer_alias = prefer_alias
        self.schema_registry = schema_registry or SchemaRegistry()
        self.signature_namespace = signature_namespace or {}

    @classmethod
    def from_openapi_context(cls, context: OpenAPIContext, prefer_alias: bool = True, **kwargs: Any) -> Self:
        kwargs.setdefault("generate_examples", context.openapi_config.create_examples)
        kwargs.setdefault("generate_component_examples", context.openapi_config.create_examples)
        kwargs.setdefault("plugins", context.plugins)
        kwargs.setdefault("schema_registry", context.schema_registry)
        return cls(**kwargs, prefer_alias=prefer_alias)

    @property
    def not_generating_examples(self) -> SchemaCreator:
        """Return a SchemaCreator with generate_examples set to False."""
        if not self.generate_examples:
            return self
        return type(self)(
            generate_examples=False,
            plugins=self.plugins,
            prefer_alias=False,
            schema_registry=self.schema_registry,
            signature_namespace=self.signature_namespace,
            generate_component_examples=self.generate_component_examples,
        )

    @staticmethod
    def plugin_supports_field(plugin: OpenAPISchemaPlugin, field: FieldDefinition) -> bool:
        if predicate := getattr(plugin, "is_plugin_supported_field", None):
            return predicate(field)  # type: ignore[no-any-return]
        return plugin.is_plugin_supported_type(field.annotation)

    def get_plugin_for(self, field_definition: FieldDefinition) -> OpenAPISchemaPlugin | None:
        return next(
            (plugin for plugin in self.plugins if self.plugin_supports_field(plugin, field_definition)),
            None,
        )

    def is_constrained_field(self, field_definition: FieldDefinition) -> bool:
        """Return if the field is constrained, taking into account constraints defined by plugins"""
        return (
            isinstance(field_definition.kwarg_definition, KwargDefinition)
            and field_definition.kwarg_definition.is_constrained
        ) or any(
            p.is_constrained_field(field_definition)
            for p in self.plugins
            if isinstance(p, OpenAPISchemaPlugin) and p.is_plugin_supported_field(field_definition)
        )

    def is_undefined(self, value: Any) -> bool:
        """Return if the field is undefined, taking into account undefined types defined by plugins"""
        return is_undefined_sentinel(value) or any(
            p.is_undefined_sentinel(value) for p in self.plugins if isinstance(p, OpenAPISchemaPlugin)
        )

    def for_field_definition(self, field_definition: FieldDefinition) -> Schema | Reference:
        """Create a Schema for a given FieldDefinition.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """

        result: Schema | Reference

        if field_definition.is_new_type:
            return self.for_new_type(field_definition)
        if is_type_alias(field_definition.annotation):
            return self.for_type_alias_type(field_definition)

        if plugin_for_annotation := self.get_plugin_for(field_definition):
            result = self.for_plugin(field_definition, plugin_for_annotation)
            if isinstance(result, Schema):
                result = self.schema_registry.get_reference_for_schema(result) or copy(result)
        elif _should_create_literal_schema(field_definition):
            annotation = (
                make_non_optional_union(field_definition.annotation)
                if field_definition.is_optional
                else field_definition.annotation
            )
            result = create_literal_schema(
                annotation,
                include_null=field_definition.is_optional,
            )
        elif field_definition.is_subclass_of(UploadFile) or (
            # optional handler-level upload bodies keep their multipart schema; optionality
            # is expressed through `requestBody.required` instead of a `oneOf` with `null`
            field_definition.is_optional
            and field_definition.name == "data"
            and isinstance(field_definition.kwarg_definition, BodyKwarg)
            and all(
                t.is_none_type or t.is_subclass_of(UploadFile) or t.has_inner_subclass_of(UploadFile)
                for t in field_definition.inner_types
            )
        ):
            result = self.for_upload_file(
                FieldDefinition.from_kwarg(
                    annotation=make_non_optional_union(field_definition.annotation),
                    name=field_definition.name,
                    default=field_definition.default,
                    kwarg_definition=field_definition.kwarg_definition,
                )
                if field_definition.is_optional
                else field_definition
            )
        elif field_definition.is_optional:
            result = self.for_optional_field(field_definition)
        elif field_definition.is_enum and not field_definition.is_union:
            result = self.for_enum_field(field_definition)
        elif field_definition.is_union:
            result = self.for_union_field(field_definition)
        elif field_definition.is_type_var:
            result = self.for_typevar()
        elif self.is_constrained_field(field_definition):
            result = self.for_constrained_field(field_definition)
        elif (field_definition.inner_types or _is_empty_tuple(field_definition)) and not field_definition.is_generic:
            # this case does not recurse for all base cases, so it needs to happen
            # after all non-concrete cases
            result = self.for_object_type(field_definition)
        else:
            result = create_schema_for_annotation(field_definition.annotation)

        if isinstance(result, Reference):
            return self._for_reference(field_definition, result)
        return self.process_schema_result(field_definition, result)

    def _for_reference(self, field_definition: FieldDefinition, reference: Reference) -> Schema | Reference:
        """Return ``reference``, wrapped in an ``allOf`` schema if the field carries metadata of its own.

        Component schemas are shared between all their usages, so metadata that belongs to a single usage is never
        written to the component. A field declaring a ``schema_component_key`` names a component of its own, which
        does receive the field's metadata.
        """
        wrapper = Schema()
        registered_schema = self.schema_registry.from_reference(reference)
        if registered_schema.key == (_get_component_key_override(field_definition),):
            self._apply_field_metadata(field_definition, registered_schema.schema)
            self._apply_kwarg_definition_metadata(field_definition, wrapper)
        else:
            self._apply_field_metadata(field_definition, wrapper)
        if wrapper == Schema():
            return reference
        wrapper.all_of = [reference]
        return wrapper

    def for_new_type(self, field_definition: FieldDefinition) -> Schema | Reference:
        return self.for_field_definition(
            FieldDefinition.from_kwarg(
                annotation=unwrap_new_type(field_definition.annotation),
                name=field_definition.name,
                default=field_definition.default,
                kwarg_definition=field_definition.kwarg_definition,
            )
        )

    def for_type_alias_type(self, field_definition: FieldDefinition) -> Schema | Reference:
        annotation = field_definition.annotation
        if not is_recursive_type_alias(annotation):
            value_field = FieldDefinition.from_annotation(resolve_type_alias(annotation))
            return self.for_field_definition(
                FieldDefinition.from_kwarg(
                    annotation=value_field.annotation,
                    name=field_definition.name,
                    default=field_definition.default,
                    kwarg_definition=_merge_kwarg_definitions(
                        value_field.kwarg_definition, field_definition.kwarg_definition
                    ),
                )
            )

        alias_field = FieldDefinition.from_annotation(annotation)
        if (reference := self.schema_registry.get_reference_for_field_definition(alias_field)) is None:
            component = self.schema_registry.get_schema_for_field_definition(alias_field)
            value_schema = self.not_generating_examples.for_field_definition(
                FieldDefinition.from_annotation(resolve_type_alias(annotation))
            )
            if isinstance(value_schema, Reference):
                component.one_of = [value_schema]
            else:
                for schema_field in dataclasses.fields(Schema):
                    setattr(component, schema_field.name, getattr(value_schema, schema_field.name))
            reference = cast("Reference", self.schema_registry.get_reference_for_field_definition(alias_field))
        result = self._for_reference(field_definition, reference)
        if isinstance(result, Schema) and result.all_of == [reference]:
            result.all_of, result.one_of = None, [reference]
        return result

    @staticmethod
    def for_upload_file(field_definition: FieldDefinition) -> Schema:
        """Create schema for UploadFile.

        Args:
            field_definition: A field definition instance.

        Returns:
            A Schema instance.
        """

        property_key = "file"
        schema = Schema(
            type=OpenAPIType.STRING,
            content_media_type="application/octet-stream",
            format=OpenAPIFormat.BINARY,
        )

        # If the type is `dict[str, UploadFile]`, then it's the same as a `list[UploadFile]`
        # but we will internally convert that into a `dict[str, UploadFile]`.
        if field_definition.is_non_string_sequence or field_definition.is_mapping:
            property_key = "files"
            schema = Schema(type=OpenAPIType.ARRAY, items=schema)
            if isinstance(kwarg_definition := field_definition.kwarg_definition, KwargDefinition):
                schema.min_items = kwarg_definition.min_items or kwarg_definition.min_length
                schema.max_items = kwarg_definition.max_items or kwarg_definition.max_length

        # If the uploadfile is annotated directly on the handler, then the
        # 'properties' needs to be created. Else, the 'properties' will be
        # created by the corresponding plugin.
        is_defined_on_handler = field_definition.name == "data" and isinstance(
            field_definition.kwarg_definition, BodyKwarg
        )
        if is_defined_on_handler:
            return Schema(type=OpenAPIType.OBJECT, properties={property_key: schema})

        return schema

    @staticmethod
    def for_typevar() -> Schema:
        """Create a schema for a TypeVar.

        Returns:
            A schema instance.
        """

        return Schema(type=OpenAPIType.OBJECT)

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
            )
        )
        # nullable scalars are expressed as 'type: [X, null]' rather than 'oneOf: [X, null]',
        # which tooling handles better (e.g. Swagger UI file inputs). refs, unions, enums and
        # const cannot preserve their semantics in a type array; structured types could, but
        # downstream tooling support is weak, so both keep the oneOf encoding.
        if (
            isinstance(schema_or_reference, Schema)
            and isinstance(schema_type := schema_or_reference.type, OpenAPIType)
            and schema_type in (OpenAPIType.STRING, OpenAPIType.INTEGER, OpenAPIType.NUMBER, OpenAPIType.BOOLEAN)
            and schema_or_reference.one_of is None
            and schema_or_reference.any_of is None
            and schema_or_reference.all_of is None
            and schema_or_reference.enum is None
            and schema_or_reference.const is None
        ):
            schema = copy(schema_or_reference)
            schema.type = [schema_type, OpenAPIType.NULL]
            return schema

        if isinstance(schema_or_reference, Schema) and isinstance(schema_or_reference.one_of, list):
            result = schema_or_reference.one_of
        else:
            result = [schema_or_reference]

        return Schema(one_of=[*result, Schema(type=OpenAPIType.NULL)])

    def for_union_field(self, field_definition: FieldDefinition) -> Schema:
        """Create a Schema for a union FieldDefinition.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        inner_types = (f for f in (field_definition.inner_types or []) if not self.is_undefined(f.annotation))
        values = list(map(self.for_field_definition, inner_types))
        return Schema(one_of=values)

    def for_object_type(self, field_definition: FieldDefinition) -> Schema:
        """Create schema for object types (dict, Mapping, list, Sequence etc.) types.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        if field_definition.has_inner_subclass_of(UploadFile):
            return self.for_upload_file(field_definition)

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
            # filters out ellipsis from tuple[int, ...] type annotations
            inner_types = tuple(f for f in field_definition.inner_types if f.annotation is not Ellipsis)

            # Handle tuple elements using prefixItems
            if (field_definition.origin is tuple) and inner_types == field_definition.inner_types:
                return Schema(
                    type=OpenAPIType.ARRAY,
                    prefix_items=[self.for_field_definition(f) for f in inner_types] or None,
                    min_items=len(inner_types),
                    max_items=len(inner_types),
                )

            # Handle other sequence types normally
            items = list(map(self.for_field_definition, inner_types))

            return Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(one_of=items) if len(items) > 1 else items[0],
            )

        raise ImproperlyConfiguredException(  # pragma: no cover
            f"Parameter '{field_definition.name}' with type '{field_definition.annotation}' could not be mapped to an Open API type. "
            f"This can occur if a user-defined generic type is resolved as a parameter. If '{field_definition.name}' should "
            "not be documented as a parameter, annotate it using the `Dependency` function, e.g., "
            f"`{field_definition.name}: ... = Dependency(...)`."
        )

    def for_plugin(self, field_definition: FieldDefinition, plugin: OpenAPISchemaPlugin) -> Schema | Reference:
        """Create a schema using a plugin.

        Args:
            field_definition: A signature field instance.
            plugin: A plugin for the field type.

        Returns:
            A schema instance.
        """
        if (ref := self.schema_registry.get_reference_for_field_definition(field_definition)) is not None:
            component = self.schema_registry.from_reference(ref).schema
            if component.properties is not None:
                self._generate_component_examples(field_definition, component)
            return ref

        schema = plugin.to_openapi_schema(field_definition=field_definition, schema_creator=self)
        if isinstance(schema, SchemaDataContainer):  # pragma: no cover
            return self.for_field_definition(
                FieldDefinition.from_kwarg(
                    annotation=schema.data_container,
                    name=field_definition.name,
                    default=field_definition.default,
                    extra=field_definition.extra,
                    kwarg_definition=field_definition.kwarg_definition,
                )
            )
        return schema

    def for_constrained_field(self, field: FieldDefinition) -> Schema:
        """Create Schema for Pydantic Constrained fields (created using constr(), conint() and so forth, or by subclassing
        Constrained*)

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        kwarg_definition = cast("KwargDefinition", field.kwarg_definition)
        annotation = field.annotation
        if any(is_class_and_subclass(annotation, t) for t in (str, bytes)):
            return create_string_constrained_field_schema(annotation, kwarg_definition)
        if any(is_class_and_subclass(annotation, t) for t in (int, float)) and not is_class_and_subclass(
            annotation, bool
        ):
            return create_numerical_constrained_field_schema(annotation, kwarg_definition)
        if field.is_mapping or field.is_non_string_iterable:
            return self.for_collection_constrained_field(field)
        return create_schema_for_annotation(annotation)

    def for_collection_constrained_field(self, field_definition: FieldDefinition) -> Schema:
        """Create Schema from Constrained List/Set field.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema instance.
        """
        if field_definition.inner_types or _is_empty_tuple(field_definition):
            schema = self.not_generating_examples.for_object_type(field_definition)
        else:
            schema = Schema(type=OpenAPIType.OBJECT if field_definition.is_mapping else OpenAPIType.ARRAY)
        if any(is_class_and_subclass(field_definition.annotation, t) for t in (set, frozenset)):
            schema.unique_items = True
        return schema

    def for_enum_field(
        self,
        field_definition: FieldDefinition,
    ) -> Schema | Reference:
        """Create a schema instance for an enum.

        Args:
            field_definition: A signature field instance.

        Returns:
            A schema or reference instance.
        """
        enum_type: None | OpenAPIType | list[OpenAPIType] = None
        if issubclass(field_definition.annotation, Enum):  # pragma: no branch
            # This method is only called for enums, so this branch is always executed
            if issubclass(field_definition.annotation, str):  # StrEnum
                enum_type = OpenAPIType.STRING
            elif issubclass(field_definition.annotation, int):  # IntEnum
                enum_type = OpenAPIType.INTEGER

        enum_values: list[Any] = [v.value for v in field_definition.annotation]
        if enum_type is None:
            enum_type = _types_in_list(enum_values)

        schema = self.schema_registry.get_schema_for_field_definition(field_definition)
        if schema.enum is None:
            schema.type = enum_type
            schema.enum = enum_values
            schema.title = get_name(field_definition.annotation)
            schema.description = field_definition.annotation.__doc__
        self._generate_component_examples(field_definition, schema)

        return self.schema_registry.get_reference_for_field_definition(field_definition) or schema

    def _generate_component_examples(self, type_: FieldDefinition, schema: Schema) -> None:
        if not schema.examples and self.generate_component_examples:
            from litestar._openapi.schema_generation.examples import create_examples_for_field

            schema.examples = get_json_schema_formatted_examples(
                create_examples_for_field(FieldDefinition.from_annotation(type_.annotation))
            )

    def _apply_kwarg_definition_metadata(self, field: FieldDefinition, schema: Schema) -> None:
        if field.kwarg_definition:
            for kwarg_definition_key, schema_key in KWARG_DEFINITION_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
                value = getattr(field.kwarg_definition, kwarg_definition_key, Empty)
                if schema_key in _NUMERIC_BOUND_PROPERTIES:
                    if not _is_numeric_bound(value, schema):
                        continue
                    if isinstance(value, Decimal):
                        value = float(value)
                elif not value or (isinstance(value, Hashable) and self.is_undefined(value)):
                    continue
                if schema_key == "examples":
                    value = get_json_schema_formatted_examples(cast("list[Example]", value))
                if kwarg_definition_key in _LENGTH_BOUND_INDEX:
                    if (length_property := _get_length_property(kwarg_definition_key, schema)) is None:
                        continue
                    schema_key = length_property

                # we only want to transfer values from the `KwargDefinition` to `Schema` if the schema object
                # doesn't already have a value for that property.
                if getattr(schema, schema_key, None) is None:
                    setattr(schema, schema_key, value)
            if schema.description is None and (description := _describe_date_bounds(field.kwarg_definition)):
                schema.description = description

    def process_schema_result(self, field: FieldDefinition, schema: Schema) -> Schema | Reference:
        """Apply the metadata of ``field`` to ``schema``.

        If ``schema`` is a component schema, it is left untouched and a reference to it is returned, wrapped in an
        ``allOf`` schema holding the metadata.
        """
        if (reference := self.schema_registry.get_reference_for_schema(schema)) is not None:
            return self._for_reference(field, reference)

        self._apply_field_metadata(field, schema)

        if not schema.examples and self.generate_examples:
            from litestar._openapi.schema_generation.examples import create_examples_for_field

            schema.examples = get_json_schema_formatted_examples(create_examples_for_field(field))

        return schema

    def _apply_field_metadata(self, field: FieldDefinition, schema: Schema) -> None:
        if field.kwarg_definition and field.is_const and field.has_default and schema.const is None:
            schema.const = field.default

        self._apply_kwarg_definition_metadata(field, schema)

        if isinstance(field.kwarg_definition, KwargDefinition) and (extra := field.kwarg_definition.schema_extra):
            field_aliases = schema.field_aliases()
            for schema_key, value in extra.items():
                if schema_key.startswith("x-"):
                    schema.extensions = {**(schema.extensions or {}), schema_key: value}
                    continue
                schema_key = field_aliases.get(schema_key, schema_key)
                if schema_key == "extensions" or not hasattr(schema, schema_key):
                    raise ValueError(
                        f"`schema_extra` declares key `{schema_key}` which does not exist in `Schema` object "
                        f"(declared by `{field.name}`). Keys must be attributes of `Schema`, their OpenAPI names, "
                        "or specification extensions starting with `x-`"
                    )
                setattr(schema, schema_key, value)

        if schema.default is None and field.default is not Empty:
            schema.default = field.default

    def create_component_schema(
        self,
        type_: FieldDefinition,
        /,
        required: list[str],
        property_fields: Mapping[str, FieldDefinition],
        openapi_type: OpenAPIType = OpenAPIType.OBJECT,
        title: str | None = None,
        examples: list[Any] | None = None,
    ) -> Schema:
        """Create a schema for the components/schemas section of the OpenAPI spec.

        These are schemas that can be referenced by other schemas in the document, including self references.

        To support self referencing schemas, the schema is added to the registry before schemas for its properties
        are created. This allows the schema to be referenced by its properties.

        Args:
            type_: ``FieldDefinition`` instance of the type to create a schema for.
            required: A list of required fields.
            property_fields: Mapping of name to ``FieldDefinition`` instances for the properties of the schema.
            openapi_type: The OpenAPI type, defaults to ``OpenAPIType.OBJECT``.
            title: The schema title, generated if not provided.
            examples: A mapping of example names to ``Example`` instances, not required.

        Returns:
            A schema instance.
        """
        schema = self.schema_registry.get_schema_for_field_definition(type_)
        schema.title = title or _get_type_schema_name(type_)
        schema.required = required
        schema.type = openapi_type
        schema.properties = {k: self.for_field_definition(v) for k, v in property_fields.items()}
        schema.examples = examples
        self._generate_component_examples(type_, schema)
        return schema
