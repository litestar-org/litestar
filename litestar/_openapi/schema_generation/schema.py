from __future__ import annotations

from collections import deque
from copy import copy
from dataclasses import MISSING, fields
from datetime import date, datetime, time, timedelta
from enum import EnumMeta
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

from _decimal import Decimal
from msgspec.structs import fields as msgspec_struct_fields
from polyfactory.utils.predicates import is_safe_subclass
from typing_extensions import NotRequired, Required, get_args, get_type_hints

from litestar._openapi.schema_generation.constrained_fields import (
    create_date_constrained_field_schema,
    create_numerical_constrained_field_schema,
    create_string_constrained_field_schema,
)
from litestar._openapi.schema_generation.examples import create_examples_for_field
from litestar._openapi.schema_generation.utils import sort_schemas_and_references
from litestar._signature.field import SignatureField
from litestar.constants import UNDEFINED_SENTINELS
from litestar.datastructures import UploadFile
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import Example, Reference
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.schema import Schema, SchemaDataContainer
from litestar.pagination import ClassicPagination, CursorPagination, OffsetPagination
from litestar.params import BodyKwarg, ParameterKwarg
from litestar.serialization import encode_json
from litestar.types import DataclassProtocol, Empty, TypedDictClass
from litestar.utils.predicates import (
    is_attrs_class,
    is_dataclass_class,
    is_optional_union,
    is_pydantic_constrained_field,
    is_pydantic_model_class,
    is_struct_class,
    is_typed_dict,
)
from litestar.utils.typing import get_origin_or_inner_type, make_non_optional_union

if TYPE_CHECKING:
    from msgspec import Struct

    from litestar.plugins import OpenAPISchemaPluginProtocol

    try:
        from pydantic import (
            BaseModel,
            ConstrainedBytes,
            ConstrainedDate,
            ConstrainedDecimal,
            ConstrainedFloat,
            ConstrainedFrozenSet,
            ConstrainedInt,
            ConstrainedList,
            ConstrainedSet,
            ConstrainedStr,
        )
        from pydantic.fields import ModelField
    except ImportError:
        BaseModel = Any  # type: ignore
        ConstrainedBytes = Any  # type: ignore
        ConstrainedDate = Any  # type: ignore
        ConstrainedDecimal = Any  # type: ignore
        ConstrainedFloat = Any  # type: ignore
        ConstrainedFrozenSet = Any  # type: ignore
        ConstrainedInt = Any  # type: ignore
        ConstrainedList = Any  # type: ignore
        ConstrainedSet = Any  # type: ignore
        ConstrainedStr = Any  # type: ignore
        ModelField = Any  # type: ignore

    try:
        from attrs import AttrsInstance
    except ImportError:
        AttrsInstance = Any  # type: ignore
try:
    import pydantic

    PYDANTIC_TYPE_MAP: dict[type[Any] | None | Any, Schema] = {
        pydantic.UUID1: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.UUID,
            description="UUID1 string",
        ),
        pydantic.UUID3: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.UUID,
            description="UUID3 string",
        ),
        pydantic.UUID4: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.UUID,
            description="UUID4 string",
        ),
        pydantic.UUID5: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.UUID,
            description="UUID5 string",
        ),
        pydantic.AnyHttpUrl: Schema(
            type=OpenAPIType.STRING, format=OpenAPIFormat.URL, description="must be a valid HTTP based URL"
        ),
        pydantic.AnyUrl: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URL),
        pydantic.ByteSize: Schema(type=OpenAPIType.INTEGER),
        pydantic.DirectoryPath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
        pydantic.EmailStr: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL),
        pydantic.FilePath: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI_REFERENCE),
        pydantic.HttpUrl: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.URL,
            description="must be a valid HTTP based URL",
            max_length=2083,
        ),
        pydantic.IPvAnyAddress: Schema(
            one_of=[
                Schema(
                    type=OpenAPIType.STRING,
                    format=OpenAPIFormat.IPV4,
                    description="IPv4 address",
                ),
                Schema(
                    type=OpenAPIType.STRING,
                    format=OpenAPIFormat.IPV6,
                    description="IPv6 address",
                ),
            ]
        ),
        pydantic.IPvAnyInterface: Schema(
            one_of=[
                Schema(
                    type=OpenAPIType.STRING,
                    format=OpenAPIFormat.IPV4,
                    description="IPv4 interface",
                ),
                Schema(
                    type=OpenAPIType.STRING,
                    format=OpenAPIFormat.IPV6,
                    description="IPv6 interface",
                ),
            ]
        ),
        pydantic.IPvAnyNetwork: Schema(
            one_of=[
                Schema(
                    type=OpenAPIType.STRING,
                    format=OpenAPIFormat.IPV4,
                    description="IPv4 network",
                ),
                Schema(
                    type=OpenAPIType.STRING,
                    format=OpenAPIFormat.IPV6,
                    description="IPv6 network",
                ),
            ]
        ),
        pydantic.Json: Schema(type=OpenAPIType.OBJECT, format=OpenAPIFormat.JSON_POINTER),
        pydantic.NameEmail: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL, description="Name and email"),
        pydantic.NegativeFloat: Schema(type=OpenAPIType.NUMBER, exclusive_maximum=0.0),
        pydantic.NegativeInt: Schema(type=OpenAPIType.INTEGER, exclusive_maximum=0),
        pydantic.NonNegativeInt: Schema(type=OpenAPIType.INTEGER, minimum=0),
        pydantic.NonPositiveFloat: Schema(type=OpenAPIType.NUMBER, maximum=0.0),
        pydantic.PaymentCardNumber: Schema(type=OpenAPIType.STRING, min_length=12, max_length=19),
        pydantic.PositiveFloat: Schema(type=OpenAPIType.NUMBER, exclusive_minimum=0.0),
        pydantic.PositiveInt: Schema(type=OpenAPIType.INTEGER, exclusive_minimum=0),
        pydantic.PostgresDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="postgres DSN"),
        pydantic.PyObject: Schema(
            type=OpenAPIType.STRING,
            description="dot separated path identifying a python object, e.g. 'decimal.Decimal'",
        ),
        pydantic.RedisDsn: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI, description="redis DSN"),
        pydantic.SecretBytes: Schema(type=OpenAPIType.STRING),
        pydantic.SecretStr: Schema(type=OpenAPIType.STRING),
        pydantic.StrictBool: Schema(type=OpenAPIType.BOOLEAN),
        pydantic.StrictBytes: Schema(type=OpenAPIType.STRING),
        pydantic.StrictFloat: Schema(type=OpenAPIType.NUMBER),
        pydantic.StrictInt: Schema(type=OpenAPIType.INTEGER),
        pydantic.StrictStr: Schema(type=OpenAPIType.STRING),
    }
except ImportError:
    PYDANTIC_TYPE_MAP = {}


KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP: dict[str, str] = {
    "default": "default",
    "multiple_of": "multipleOf",
    "ge": "minimum",
    "le": "maximum",
    "lt": "exclusiveMaximum",
    "gt": "exclusiveMinimum",
    "max_length": "maxLength",
    "min_length": "minLength",
    "max_items": "maxItems",
    "min_items": "minItems",
    "pattern": "pattern",
    "title": "title",
    "description": "description",
    "examples": "examples",
    "external_docs": "externalDocs",
    "content_encoding": "contentEncoding",
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
    # pydantic types
    **PYDANTIC_TYPE_MAP,
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
            yield arg


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
    __slots__ = ("generate_examples", "plugins", "schemas", "prefer_alias")

    def __init__(
        self,
        generate_examples: bool = False,
        plugins: list[OpenAPISchemaPluginProtocol] | None = None,
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

    def for_field(self, field: SignatureField) -> Schema | Reference:
        """Create a Schema for a given SignatureField.

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        result: Schema | Reference
        if field.is_optional:
            result = self.for_optional_field(field)
        elif field.is_union:
            result = self.for_union_field(field)
        elif is_pydantic_model_class(field.field_type):
            result = self.for_pydantic_model(field.field_type)
        elif is_attrs_class(field.field_type):
            result = self.for_attrs_class(field.field_type)
        elif is_struct_class(field.field_type):
            result = self.for_struct_class(field.field_type)
        elif is_dataclass_class(field.field_type):
            result = self.for_dataclass(field.field_type)
        elif is_typed_dict(field.field_type):
            result = self.for_typed_dict(field.field_type)
        elif plugins_for_annotation := [
            plugin for plugin in self.plugins if plugin.is_plugin_supported_type(field.field_type)
        ]:
            result = self.for_plugin(field, plugins_for_annotation[0])
        elif is_pydantic_constrained_field(field.field_type) or (
            isinstance(field.kwarg_model, (ParameterKwarg, BodyKwarg)) and field.kwarg_model.is_constrained
        ):
            result = self.for_constrained_field(field)
        elif field.children and not field.is_generic:
            result = self.for_object_type(field)
        elif field.is_generic and (
            get_origin_or_inner_type(field.field_type) in (ClassicPagination, CursorPagination, OffsetPagination)
        ):
            result = self.for_builtin_generics(field)
        else:
            result = create_schema_for_annotation(field.field_type)

        return self.process_schema_result(field, result) if isinstance(result, Schema) else result

    def for_optional_field(self, field: SignatureField) -> Schema:
        """Create a Schema for an optional SignatureField.

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        schema_or_reference = self.for_field(
            SignatureField.create(
                field_type=make_non_optional_union(field.field_type),
                name=field.name,
                default_value=field.default_value,
            )
        )
        if isinstance(schema_or_reference, Schema) and isinstance(schema_or_reference.one_of, list):
            result = schema_or_reference.one_of
        else:
            result = [schema_or_reference]

        return Schema(one_of=[Schema(type=OpenAPIType.NULL), *result])

    def for_union_field(self, field: SignatureField) -> Schema:
        """Create a Schema for a union SignatureField.

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        return Schema(one_of=sort_schemas_and_references(list(map(self.for_field, field.children or []))))

    def for_object_type(self, field: SignatureField) -> Schema:
        """Create schema for object types (dict, Mapping, list, Sequence etc.) types.

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        if field.is_mapping:
            return Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=(
                    self.for_field(field.children[1]) if field.children and len(field.children) == 2 else None
                ),
            )

        if field.is_non_string_sequence or field.is_non_string_iterable:
            items = list(map(self.for_field, field.children or ()))
            return Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(one_of=sort_schemas_and_references(items)) if len(items) > 1 else items[0],
            )

        if field.is_literal:
            return create_literal_schema(field.field_type)

        raise ImproperlyConfiguredException(
            f"Parameter '{field.name}' with type '{field.field_type}' could not be mapped to an Open API type. "
            f"This can occur if a user-defined generic type is resolved as a parameter. If '{field.name}' should "
            "not be documented as a parameter, annotate it using the `Dependency` function, e.g., "
            f"`{field.name}: ... = Dependency(...)`."
        )

    def for_builtin_generics(self, field: SignatureField) -> Schema:
        """Handle builtin generic types.

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        origin = get_origin_or_inner_type(field.field_type)
        if origin is ClassicPagination:
            return Schema(
                type=OpenAPIType.OBJECT,
                properties={
                    "items": Schema(
                        type=OpenAPIType.ARRAY,
                        items=self.for_field(field.children[0]),  # type: ignore[index]
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
                        items=self.for_field(field.children[0]),  # type: ignore[index]
                    ),
                    "limit": Schema(type=OpenAPIType.INTEGER, description="Maximal number of items to send."),
                    "offset": Schema(type=OpenAPIType.INTEGER, description="Offset from the beginning of the query."),
                    "total": Schema(type=OpenAPIType.INTEGER, description="Total number of items."),
                },
            )

        cursor_schema = self.not_generating_examples.for_field(field.children[0])  # type: ignore[index]
        cursor_schema.description = "Unique ID, designating the last identifier in the given data set. This value can be used to request the 'next' batch of records."

        return Schema(
            type=OpenAPIType.OBJECT,
            properties={
                "items": Schema(
                    type=OpenAPIType.ARRAY, items=self.for_field(field=field.children[1])  # type: ignore[index]
                ),
                "cursor": cursor_schema,
                "results_per_page": Schema(type=OpenAPIType.INTEGER, description="Maximal number of items to send."),
            },
        )

    def for_plugin(self, field: SignatureField, plugin: OpenAPISchemaPluginProtocol) -> Schema | Reference:
        """Create a schema using a plugin.

        Args:
            field: A signature field instance.
            plugin: A plugin for the field type.

        Returns:
            A schema instance.
        """
        schema = plugin.to_openapi_schema(field.field_type)
        if isinstance(schema, SchemaDataContainer):
            return self.for_field(
                SignatureField.create(
                    field_type=schema.data_container,
                    name=field.name,
                    default_value=field.default_value,
                    extra=field.extra,
                    kwarg_model=field.kwarg_model,
                )
            )
        return schema  # pragma: no cover

    def for_pydantic_model(self, field_type: type[BaseModel]) -> Schema:
        """Create a schema object for a given pydantic model class.

        Args:
            field_type: A pydantic model class.

        Returns:
            A schema instance.
        """
        field_type_hints = get_type_hints(field_type, include_extras=True)
        model_config = getattr(field_type, "__config__", getattr(field_type, "model_config", Empty))
        if isinstance(model_config, dict):
            title = model_config.get("title")
            example = model_config.get("example")
        else:
            title = getattr(model_config, "title", None)
            example = getattr(model_config, "example", None)

        return Schema(
            required=sorted(self.get_field_name(field) for field in field_type.__fields__.values() if field.required),
            properties={
                self.get_field_name(f): self.for_field(
                    SignatureField.create(
                        field_type=field_type_hints[f.name], name=self.get_field_name(f), default_value=f.field_info
                    )
                )
                for f in field_type.__fields__.values()
            },
            type=OpenAPIType.OBJECT,
            title=title or _get_type_schema_name(field_type),
            examples=[Example(example)] if example else None,
        )

    def for_attrs_class(self, field_type: type[AttrsInstance]) -> Schema:
        """Create a schema object for a given attrs class.

        Args:
            field_type: An attrs class.

        Returns:
            A schema instance.
        """
        from attr import NOTHING
        from attrs import fields_dict

        field_type_hints = get_type_hints(field_type, include_extras=True)
        return Schema(
            required=sorted(
                [
                    field_name
                    for field_name, attribute in fields_dict(field_type).items()
                    if attribute.default is NOTHING and not is_optional_union(field_type_hints[field_name])
                ]
            ),
            properties={k: self.for_field(SignatureField.create(v, k)) for k, v in field_type_hints.items()},
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(field_type),
        )

    def for_struct_class(self, field_type: type[Struct]) -> Schema:
        """Create a schema object for a given msgspec.Struct class.

        Args:
            field_type: A msgspec.Struct class.

        Returns:
            A schema instance.
        """
        return Schema(
            required=sorted(
                [
                    field.encode_name
                    for field in msgspec_struct_fields(field_type)
                    if field.required and not is_optional_union(field.type)
                ]
            ),
            properties={
                field.encode_name: self.for_field(SignatureField.create(field.type, field.encode_name))
                for field in msgspec_struct_fields(field_type)
            },
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(field_type),
        )

    def for_dataclass(self, field_type: type[DataclassProtocol]) -> Schema:
        """Create a schema object for a given dataclass class.

        Args:
            field_type: A dataclass class.

        Returns:
            A schema instance.
        """
        field_type_hints = get_type_hints(field_type, include_extras=True)
        return Schema(
            required=sorted(
                [
                    field.name
                    for field in fields(field_type)
                    if (
                        field.default is MISSING
                        and field.default_factory is MISSING
                        and not is_optional_union(field_type_hints[field.name])
                    )
                ]
            ),
            properties={k: self.for_field(SignatureField.create(v, k)) for k, v in field_type_hints.items()},
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(field_type),
        )

    def for_typed_dict(self, field_type: TypedDictClass) -> Schema:
        """Create a schema object for a given typed dict.

        Args:
            field_type: A typed-dict class.

        Returns:
            A schema instance.
        """
        annotations: dict[str, Any] = {}
        for k, v in get_type_hints(field_type, include_extras=True).items():
            if get_origin(v) in (Required, NotRequired):
                annotations[k] = get_args(v)[0]
            else:
                annotations[k] = v

        return Schema(
            required=sorted(getattr(field_type, "__required_keys__", [])),
            properties={k: self.for_field(SignatureField.create(v, k)) for k, v in annotations.items()},
            type=OpenAPIType.OBJECT,
            title=_get_type_schema_name(field_type),
        )

    def for_constrained_field(self, field: SignatureField) -> Schema:
        """Create Schema for Pydantic Constrained fields (created using constr(), conint() and so forth, or by subclassing
        Constrained*)

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        kwargs_model = cast(Union[ParameterKwarg, BodyKwarg], field.kwarg_model)
        if any(is_safe_subclass(field.field_type, t) for t in (int, float, Decimal)):
            return create_numerical_constrained_field_schema(field.field_type, kwargs_model)
        if any(is_safe_subclass(field.field_type, t) for t in (str, bytes)):  # type: ignore[arg-type]
            return create_string_constrained_field_schema(field.field_type, kwargs_model)
        if any(is_safe_subclass(field.field_type, t) for t in (date, datetime)):
            return create_date_constrained_field_schema(field.field_type, kwargs_model)
        return self.for_collection_constrained_field(field)

    def for_collection_constrained_field(self, field: SignatureField) -> Schema:
        """Create Schema from Constrained List/Set field.

        Args:
            field: A signature field instance.

        Returns:
            A schema instance.
        """
        schema = Schema(type=OpenAPIType.ARRAY)
        kwargs_model = cast(Union[ParameterKwarg, BodyKwarg], field.kwarg_model)
        if kwargs_model.min_items:
            schema.min_items = kwargs_model.min_items
        if kwargs_model.max_items:
            schema.max_items = kwargs_model.max_items
        if any(is_safe_subclass(field.field_type, t) for t in (set, frozenset)):  # type: ignore[arg-type]
            schema.unique_items = True

        item_creator = self.not_generating_examples
        if field.children:
            items = list(map(item_creator.for_field, field.children))
            if len(items) > 1:
                schema.items = Schema(one_of=sort_schemas_and_references(items))
            else:
                schema.items = items[0]
        else:
            schema.items = item_creator.for_field(
                SignatureField.create(field.field_type.item_type, f"{field.field_type.__name__}Field")
            )
        return schema

    def get_field_name(self, field: ModelField) -> str:
        """Get the preferred name for a model field.

        Args:
            field: A model field instance.

        Returns:
            The preferred name for the field.
        """
        return (field.alias or field.name) if self.prefer_alias else field.name

    def process_schema_result(self, field: SignatureField, schema: Schema) -> Schema | Reference:
        if field.kwarg_model and field.is_const and not field.is_empty and schema.const is None:
            schema.const = field.default_value

        if field.kwarg_model:
            for kwarg_model_key, schema_key in KWARG_MODEL_ATTRIBUTE_TO_OPENAPI_PROPERTY_MAP.items():
                if (value := getattr(field.kwarg_model, kwarg_model_key, Empty)) and (
                    not isinstance(value, Hashable) or value not in UNDEFINED_SENTINELS
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
