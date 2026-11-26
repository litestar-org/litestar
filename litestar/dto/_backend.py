"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import fields, replace
from functools import partial
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Final,
    Protocol,
    Union,
    cast,
)

import msgspec
from msgspec import UNSET, Struct, UnsetType, convert, defstruct, field

from litestar.dto._codegen_backend import TransferFunctionCache, TransferFunctionFactory
from litestar.dto._types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferDTOFieldDefinition,
    TransferType,
    TupleType,
    UnionType,
)
from litestar.dto.data_structures import DTOData, DTOFieldDefinition
from litestar.dto.field import Mark
from litestar.enums import RequestEncodingType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import KwargDefinition
from litestar.serialization import decode_json, decode_msgpack, default_deserializer
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils import unique_name_for_scope

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Sequence, Set

    from litestar.connection import ASGIConnection
    from litestar.dto import AbstractDTO, RenameStrategy
    from litestar.types import TypeDecodersSequence
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("DTOBackend", "TransferModelRegistry")

_INVALID_NAME_CHARACTER = re.compile(r"[^A-Za-z0-9_]")


class CompositeTypeHandler(Protocol):
    def __call__(
        self,
        field_definition: FieldDefinition,
        exclude: Set[str],
        include: Set[str],
        rename_fields: dict[str, str],
        name: str,
        nested_depth: int,
    ) -> CompositeType: ...


class TransferModelRegistry:
    """The DTO transfer models of an application, by name"""

    __slots__ = ("_models",)

    def __init__(self) -> None:
        self._models: dict[
            tuple[str, str], tuple[Any, type[AbstractDTO], tuple[TransferDTOFieldDefinition, ...], type[Struct]]
        ] = {}

    def get_or_add(
        self,
        key: Any,
        dto_factory: type[AbstractDTO],
        field_definitions: tuple[TransferDTOFieldDefinition, ...],
        transfer_model_type: type[Struct],
    ) -> tuple[tuple[TransferDTOFieldDefinition, ...], type[Struct]]:
        """Return the transfer model registered under the module and name of ``transfer_model_type``, registering it
        with its nested transfer models if they are new.

        Raises:
            ImproperlyConfiguredException: If a transfer model of another shape is registered under the name.
        """
        name = transfer_model_type.__schema_name__  # type: ignore[attr-defined]
        if (registered := self._models.get((transfer_model_type.__module__, name))) is not None:
            registered_key, registered_dto, registered_field_definitions, registered_model = registered
            if registered_key != key:
                raise ImproperlyConfiguredException(
                    f"DTO transfer model name {name!r} is used for two different shapes, by "
                    f"{_describe_dto(registered_dto)} and {_describe_dto(dto_factory)}. Set '__schema_name__' on "
                    "one of them, or on a DTO subclass replacing it."
                )
            return registered_field_definitions, registered_model

        for nested in _iter_nested_field_info(field_definitions):
            self.get_or_add((key, nested.model.__schema_name__), dto_factory, nested.field_definitions, nested.model)
        self._models[transfer_model_type.__module__, name] = (key, dto_factory, field_definitions, transfer_model_type)
        return field_definitions, transfer_model_type


class DTOBackend:
    __slots__ = (
        "_encode_data",
        "_has_directional_fields",
        "_transfer_function_cache",
        "_transfer_model_names",
        "_transfer_to_dict",
        "_transfer_to_model_type",
        "annotation",
        "attribute_accessor",
        "dto_data_type",
        "dto_factory",
        "field_definition",
        "handler_id",
        "is_data_field",
        "model_type",
        "parsed_field_definitions",
        "reverse_name_map",
        "transfer_model_type",
        "type_decoders",
        "wrapper_attribute_name",
    )

    def __init__(
        self,
        dto_factory: type[AbstractDTO],
        field_definition: FieldDefinition,
        is_data_field: bool,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
        handler_id: str | None = None,
        *,
        transfer_models: TransferModelRegistry | None = None,
        type_decoders: TypeDecodersSequence | None = None,
    ) -> None:
        """Create dto backend instance.

        Args:
            dto_factory: The DTO factory class calling this backend.
            field_definition: Parsed type.
            is_data_field: Whether the field is a subclass of DTOData.
            model_type: Model type.
            wrapper_attribute_name: If the data that DTO should operate upon is wrapped in a generic datastructure,
                this is the name of the attribute that the data is stored in.
            handler_id: The name of the handler that this backend is for, if any.
            transfer_models: The transfer models of the application, shared by the backends that build the same one.
            type_decoders: Type decoders used when data is parsed without a connection.
        """
        self.dto_factory: Final[type[AbstractDTO]] = dto_factory
        self.field_definition: Final[FieldDefinition] = field_definition
        self.is_data_field: Final[bool] = is_data_field
        self.handler_id: Final[str | None] = handler_id
        self.type_decoders: Final[TypeDecodersSequence] = type_decoders or ()
        self.model_type: Final[type[Any]] = model_type
        self.wrapper_attribute_name: Final[str | None] = wrapper_attribute_name
        self.attribute_accessor = dto_factory.attribute_accessor
        self._transfer_model_names: set[str] = set()
        self._has_directional_fields = False

        name = self._create_transfer_model_name()
        self.parsed_field_definitions = self._parse_root_model(name)
        if self.dto_factory.__schema_name__ and self._has_directional_fields:
            name = f"{name}{self._direction_suffix}"
            self._transfer_model_names.clear()
            self.parsed_field_definitions = self._parse_root_model(name)
        self.transfer_model_type = self.create_transfer_model_type(
            model_name=name, field_definitions=self.parsed_field_definitions
        )
        if transfer_models is not None:
            self.parsed_field_definitions, self.transfer_model_type = transfer_models.get_or_add(
                key=(_dto_identity(dto_factory), model_type, _shape(self.parsed_field_definitions)),
                dto_factory=dto_factory,
                field_definitions=self.parsed_field_definitions,
                transfer_model_type=self.transfer_model_type,
            )
        self.dto_data_type: type[DTOData] | None = None

        if field_definition.is_subclass_of(DTOData):
            self.dto_data_type = field_definition.annotation
            field_definition = self.field_definition.inner_types[0]

        self.annotation = build_annotation_for_backend(model_type, field_definition, self.transfer_model_type)
        self._transfer_function_cache: TransferFunctionCache = {}
        self._transfer_to_dict = self._create_transfer_data_fn(
            destination_type=dict,
            field_definition=self.field_definition,
        )
        self._transfer_to_model_type = self._create_transfer_data_fn(
            destination_type=self.model_type,
            field_definition=self.field_definition,
        )
        self._encode_data = self._create_transfer_data_fn(
            destination_type=self.transfer_model_type,
            field_definition=self.field_definition,
        )

    @property
    def _direction_suffix(self) -> str:
        return "RequestBody" if self.is_data_field else "ResponseBody"

    def _parse_root_model(self, name: str) -> tuple[TransferDTOFieldDefinition, ...]:
        return self.parse_model(
            model_type=self.model_type,
            exclude=self.dto_factory.config.exclude,
            include=self.dto_factory.config.include,
            rename_fields=self.dto_factory.config.rename_fields,
            name=name,
        )

    def parse_model(
        self,
        model_type: Any,
        exclude: Set[str],
        include: Set[str],
        rename_fields: dict[str, str],
        nested_depth: int = 0,
        name: str | None = None,
    ) -> tuple[TransferDTOFieldDefinition, ...]:
        """Reduce :attr:`model_type` to a tuple :class:`TransferDTOFieldDefinition` instances.

        Args:
            model_type: The model to reduce.
            exclude: Names of the fields to exclude.
            include: Names of the fields to include.
            rename_fields: Serialization names by field name.
            nested_depth: The nesting depth of ``model_type``.
            name: The name of the transfer model of ``model_type``, prefix of the names of its nested transfer models.
                Defaults to the name of the root transfer model.

        Returns:
        Fields for data transfer.
        """
        if name is None:
            name = self._create_transfer_model_name()
        defined_fields = []
        generic_field_definitions = list(FieldDefinition.from_annotation(model_type).generic_types or ())
        for field_definition in self.dto_factory.generate_field_definitions(model_type):
            if field_definition.is_type_var:
                base_arg_field = generic_field_definitions.pop()
                field_definition = replace(
                    field_definition, annotation=base_arg_field.annotation, raw=base_arg_field.raw
                )

            if _should_mark_private(field_definition, self.dto_factory.config.underscore_fields_private):
                field_definition.dto_field.mark = Mark.PRIVATE

            has_directional_fields = self._has_directional_fields
            try:
                transfer_type = self._create_transfer_type(
                    field_definition=field_definition,
                    exclude=exclude,
                    include=include,
                    rename_fields=rename_fields,
                    field_name=field_definition.name,
                    name=f"{name}.{_escape(field_definition.name)}",
                    nested_depth=nested_depth,
                )
            except RecursionError:
                continue

            is_excluded = _should_exclude_field(
                field_definition=field_definition, exclude=exclude, include=include, is_data_field=self.is_data_field
            )
            is_excluded_in_other_direction = _should_exclude_field(
                field_definition=field_definition,
                exclude=exclude,
                include=include,
                is_data_field=not self.is_data_field,
            )
            if is_excluded and is_excluded_in_other_direction:
                self._has_directional_fields = has_directional_fields
            elif is_excluded != is_excluded_in_other_direction:
                self._has_directional_fields = True
            transfer_field_definition = TransferDTOFieldDefinition.from_dto_field_definition(
                field_definition=field_definition,
                serialization_name=rename_fields.get(field_definition.name),
                transfer_type=transfer_type,
                is_partial=self.dto_factory.config.partial,
                is_excluded=is_excluded,
            )
            defined_fields.append(transfer_field_definition)
        return tuple(defined_fields)

    def _create_transfer_model_name(self) -> str:
        if self.dto_factory.__schema_name__:
            return self.dto_factory.__schema_name__
        if _is_anonymous(self.dto_factory):
            name = f"{_escape(self.model_type.__name__)}{self._direction_suffix}"
            if fingerprint := _config_fingerprint(self.dto_factory, self.model_type):
                name = f"{name}_{fingerprint}"
            return name
        name = _escape(self.dto_factory.__name__)
        if self.model_type != getattr(self.dto_factory, "model_type", self.model_type):
            name += _escape(self.model_type.__name__)
        return f"{name}{self._direction_suffix}"

    def create_transfer_model_type(
        self,
        model_name: str,
        field_definitions: tuple[TransferDTOFieldDefinition, ...],
    ) -> type[Struct]:
        """Create a model for data transfer.

        Args:
            model_name: name of the transfer model.
            field_definitions: field definitions for the container type.

        Returns:
            A ``BackendT`` class.
        """
        if model_name in self._transfer_model_names:
            model_name = unique_name_for_scope(model_name, self._transfer_model_names)
        self._transfer_model_names.add(model_name)

        owner = self.model_type if _is_anonymous(self.dto_factory) else self.dto_factory
        struct = _create_struct_for_field_definitions(
            model_name=model_name,
            module=f"{__name__}.{owner.__module__}",
            field_definitions=field_definitions,
            rename_strategy=self.dto_factory.config.rename_strategy,
            forbid_unknown_fields=self.dto_factory.config.forbid_unknown_fields,
        )
        setattr(struct, "__schema_name__", model_name)
        return struct

    def parse_raw(
        self,
        raw: bytes,
        asgi_connection: ASGIConnection | None = None,
        media_type: RequestEncodingType | str | None = None,
    ) -> Struct | Collection[Struct]:
        """Parse raw bytes into transfer model type.

        Args:
            raw: bytes
            asgi_connection: The current ASGI Connection, if any.
            media_type: The media type of ``raw``. Defaults to the content type of ``asgi_connection``, or to JSON.

        Returns:
            The raw bytes parsed into transfer model type.
        """
        request_encoding = media_type or RequestEncodingType.JSON

        if (
            media_type is None
            and (content_type := getattr(asgi_connection, "content_type", None))
            and (connection_media_type := content_type[0])
        ):
            request_encoding = connection_media_type

        type_decoders = self.type_decoders if asgi_connection is None else asgi_connection.route_handler.type_decoders

        if request_encoding == RequestEncodingType.MESSAGEPACK:
            result = decode_msgpack(value=raw, target_type=self.annotation, type_decoders=type_decoders, strict=False)
        else:
            result = decode_json(value=raw, target_type=self.annotation, type_decoders=type_decoders, strict=False)

        return cast("Struct | Collection[Struct]", result)

    def parse_builtins(self, builtins: Any, asgi_connection: ASGIConnection | None = None) -> Any:
        """Parse builtin types into transfer model type.

        Args:
            builtins: Builtin type.
            asgi_connection: The current ASGI Connection, if any.

        Returns:
            The builtin type parsed into transfer model type.
        """
        return convert(
            obj=builtins,
            type=self.annotation,
            dec_hook=partial(default_deserializer, type_decoders=self.type_decoders)
            if asgi_connection is None
            else asgi_connection.route_handler.default_deserializer,
            strict=False,
            str_keys=True,
        )

    def populate_data_from_builtins(self, builtins: Any, asgi_connection: ASGIConnection | None = None) -> Any:
        """Populate model instance from builtin types.

        Args:
            builtins: Builtin type.
            asgi_connection: The current ASGI Connection, if any.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        if self.dto_data_type:
            return self.dto_data_type(
                backend=self,
                data_as_builtins=self._transfer_to_dict(self.parse_builtins(builtins, asgi_connection)),
            )
        return self.transfer_data_from_builtins(self.parse_builtins(builtins, asgi_connection))

    def transfer_data_from_builtins(self, builtins: Any) -> Any:
        """Populate model instance from builtin types.

        Args:
            builtins: Builtin type.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        return self._transfer_to_model_type(builtins)

    def populate_data_from_raw(
        self,
        raw: bytes,
        asgi_connection: ASGIConnection | None = None,
        media_type: RequestEncodingType | str | None = None,
    ) -> Any:
        """Parse raw bytes into instance of `model_type`.

        Args:
            raw: bytes
            asgi_connection: The current ASGI Connection, if any.
            media_type: The media type of ``raw``. Defaults to the content type of ``asgi_connection``, or to JSON.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        if self.dto_data_type:
            return self.dto_data_type(
                backend=self,
                data_as_builtins=self._transfer_to_dict(self.parse_raw(raw, asgi_connection, media_type)),
            )
        return self._transfer_to_model_type(self.parse_raw(raw, asgi_connection, media_type))

    def encode_data(self, data: Any) -> LitestarEncodableType:
        """Encode data into a ``LitestarEncodableType``.

        Args:
            data: Data to encode.

        Returns:
            Encoded data.
        """
        if self.wrapper_attribute_name:
            wrapped_transfer = self._encode_data(getattr(data, self.wrapper_attribute_name))
            setattr(data, self.wrapper_attribute_name, wrapped_transfer)
            return cast("LitestarEncodableType", data)

        return cast("LitestarEncodableType", self._encode_data(data))

    def _create_transfer_data_fn(
        self,
        destination_type: type[Any],
        field_definition: FieldDefinition,
    ) -> Any:
        """Create instance or iterable of instances of ``destination_type``.

        Args:
            destination_type: the model type received by the DTO on type narrowing.
            field_definition: the parsed type that represents the handler annotation for which the DTO is being applied.

        Returns:
            Data parsed into ``destination_type``.
        """
        return TransferFunctionFactory.create_transfer_data(
            destination_type=destination_type,
            field_definitions=self.parsed_field_definitions,
            is_data_field=self.is_data_field,
            field_definition=field_definition,
            attribute_accessor=self.attribute_accessor,
            cache=self._transfer_function_cache,
        )

    def _get_handler_for_field_definition(self, field_definition: FieldDefinition) -> CompositeTypeHandler | None:
        if field_definition.is_union:
            return self._create_union_type

        if field_definition.is_tuple:
            if len(field_definition.inner_types) == 2 and field_definition.inner_types[1].annotation is Ellipsis:
                return self._create_collection_type
            return self._create_tuple_type

        if field_definition.is_mapping:
            return self._create_mapping_type

        if field_definition.is_non_string_collection:
            return self._create_collection_type
        return None

    def _has_nested(self, field_definition: FieldDefinition) -> bool:
        return self.dto_factory.detect_nested_field(field_definition) or any(
            self._has_nested(inner_type) for inner_type in field_definition.inner_types
        )

    def _create_inner_names(self, name: str, inner_types: Sequence[FieldDefinition]) -> list[str]:
        if sum(self._has_nested(inner_type) for inner_type in inner_types) > 1:
            return [f"{name}.{i}" for i in range(len(inner_types))]
        return [name] * len(inner_types)

    def _create_transfer_type(
        self,
        field_definition: FieldDefinition,
        exclude: Set[str],
        include: Set[str],
        rename_fields: dict[str, str],
        field_name: str,
        name: str,
        nested_depth: int,
    ) -> CompositeType | SimpleType:
        exclude = _filter_nested_field(exclude, field_name)
        include = _filter_nested_field(include, field_name)
        rename_fields = _filter_nested_field_mapping(rename_fields, field_name)

        if composite_type_handler := self._get_handler_for_field_definition(field_definition):
            return composite_type_handler(
                field_definition=field_definition,
                exclude=exclude,
                include=include,
                rename_fields=rename_fields,
                name=name,
                nested_depth=nested_depth,
            )

        transfer_model: NestedFieldInfo | None = None

        if self.dto_factory.detect_nested_field(field_definition):
            if nested_depth == self.dto_factory.config.max_nested_depth:
                raise RecursionError

            nested_field_definitions = self.parse_model(
                model_type=field_definition.annotation,
                exclude=exclude,
                include=include,
                rename_fields=rename_fields,
                name=name,
                nested_depth=nested_depth + 1,
            )

            transfer_model = NestedFieldInfo(
                model=self.create_transfer_model_type(name, nested_field_definitions),
                field_definitions=nested_field_definitions,
            )

        return SimpleType(field_definition, nested_field_info=transfer_model)

    def _create_collection_type(
        self,
        field_definition: FieldDefinition,
        exclude: Set[str],
        include: Set[str],
        rename_fields: dict[str, str],
        name: str,
        nested_depth: int,
    ) -> CollectionType:
        inner_types = field_definition.inner_types
        inner_type = self._create_transfer_type(
            field_definition=inner_types[0] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="0",
            name=name,
            nested_depth=nested_depth,
            rename_fields=rename_fields,
        )
        return CollectionType(
            field_definition=field_definition, inner_type=inner_type, has_nested=inner_type.has_nested
        )

    def _create_mapping_type(
        self,
        field_definition: FieldDefinition,
        exclude: Set[str],
        include: Set[str],
        rename_fields: dict[str, str],
        name: str,
        nested_depth: int,
    ) -> MappingType:
        key_field, value_field = field_definition.inner_types or (FieldDefinition.from_annotation(Any),) * 2
        key_name, value_name = self._create_inner_names(name, (key_field, value_field))
        key_type = self._create_transfer_type(
            field_definition=key_field,
            exclude=exclude,
            include=include,
            field_name="0",
            name=key_name,
            nested_depth=nested_depth,
            rename_fields=rename_fields,
        )
        value_type = self._create_transfer_type(
            field_definition=value_field,
            exclude=exclude,
            include=include,
            field_name="1",
            name=value_name,
            nested_depth=nested_depth,
            rename_fields=rename_fields,
        )
        return MappingType(
            field_definition=field_definition,
            key_type=key_type,
            value_type=value_type,
            has_nested=key_type.has_nested or value_type.has_nested,
        )

    def _create_tuple_type(
        self,
        field_definition: FieldDefinition,
        exclude: Set[str],
        include: Set[str],
        rename_fields: dict[str, str],
        name: str,
        nested_depth: int,
    ) -> TupleType:
        inner_types = tuple(
            self._create_transfer_type(
                field_definition=inner_type,
                exclude=exclude,
                include=include,
                field_name=str(i),
                name=inner_name,
                nested_depth=nested_depth,
                rename_fields=rename_fields,
            )
            for i, (inner_type, inner_name) in enumerate(
                zip(
                    field_definition.inner_types,
                    self._create_inner_names(name, field_definition.inner_types),
                    strict=True,
                )
            )
        )
        return TupleType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(t.has_nested for t in inner_types),
        )

    def _create_union_type(
        self,
        field_definition: FieldDefinition,
        exclude: Set[str],
        include: Set[str],
        rename_fields: dict[str, str],
        name: str,
        nested_depth: int,
    ) -> UnionType:
        inner_types = tuple(
            self._create_transfer_type(
                field_definition=inner_type,
                exclude=exclude,
                include=include,
                field_name=str(i),
                name=inner_name,
                nested_depth=nested_depth,
                rename_fields=rename_fields,
            )
            for i, (inner_type, inner_name) in enumerate(
                zip(
                    field_definition.inner_types,
                    self._create_inner_names(name, field_definition.inner_types),
                    strict=True,
                )
            )
        )
        return UnionType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(t.has_nested for t in inner_types),
        )


def _escape(name_part: str) -> str:
    return _INVALID_NAME_CHARACTER.sub(lambda match: f"_{ord(match.group()):x}", name_part)


def _is_anonymous(dto_factory: type[AbstractDTO]) -> bool:
    return "[" in dto_factory.__name__


def _dto_identity(dto_factory: type[AbstractDTO]) -> Any:
    if _is_anonymous(dto_factory):
        return dto_factory.__bases__[0], dto_factory.config
    return dto_factory


def _config_fingerprint(dto_factory: type[AbstractDTO], model_type: type[Any]) -> str | None:
    config = dto_factory.config
    default = dto_factory.get_config_for_model_type(type(config)(), getattr(dto_factory, "model_type", model_type))
    rendered = ";".join(
        f"{name}={_render_config_value(getattr(config, name))}"
        for name in sorted(config_field.name for config_field in fields(config))
        if getattr(config, name) != getattr(default, name)
    )
    return hashlib.sha256(rendered.encode()).hexdigest()[:8] if rendered else None


def _render_config_value(value: Any) -> str:
    if isinstance(value, (set, frozenset)):
        return f"{{{','.join(sorted(map(_render_config_value, value)))}}}"
    if isinstance(value, Mapping):
        items = sorted(f"{_render_config_value(key)}:{_render_config_value(item)}" for key, item in value.items())
        return f"{{{','.join(items)}}}"
    if isinstance(value, (list, tuple)):
        return f"[{','.join(map(_render_config_value, value))}]"
    if callable(value):
        return f"{value.__module__}.{getattr(value, '__qualname__', type(value).__qualname__)}"
    return repr(value)


def _describe_dto(dto_factory: type[AbstractDTO]) -> str:
    if _is_anonymous(dto_factory):
        model_type = getattr(dto_factory, "model_type", object)
        return f"'{dto_factory.__bases__[0].__qualname__}[{model_type.__module__}.{model_type.__qualname__}]'"
    return f"'{dto_factory.__module__}.{dto_factory.__qualname__}'"


def _iter_transfer_types(transfer_type: TransferType) -> Iterator[SimpleType]:
    if isinstance(transfer_type, SimpleType):
        yield transfer_type
    elif isinstance(transfer_type, CollectionType):
        yield from _iter_transfer_types(transfer_type.inner_type)
    elif isinstance(transfer_type, MappingType):
        yield from _iter_transfer_types(transfer_type.key_type)
        yield from _iter_transfer_types(transfer_type.value_type)
    elif isinstance(transfer_type, (TupleType, UnionType)):
        for inner_type in transfer_type.inner_types:
            yield from _iter_transfer_types(inner_type)


def _iter_nested_field_info(field_definitions: tuple[TransferDTOFieldDefinition, ...]) -> Iterator[NestedFieldInfo]:
    for field_definition in field_definitions:
        for simple_type in _iter_transfer_types(field_definition.transfer_type):
            if simple_type.nested_field_info is not None:
                yield simple_type.nested_field_info


def _shape(field_definitions: tuple[TransferDTOFieldDefinition, ...]) -> tuple[Any, ...]:
    return tuple(
        (
            field_definition.name,
            field_definition.is_excluded,
            ()
            if field_definition.is_excluded
            else tuple(_shape(nested.field_definitions) for nested in _iter_nested_field_info((field_definition,))),
        )
        for field_definition in field_definitions
    )


def _filter_nested_field(field_name_set: Set[str], field_name: str) -> Set[str]:
    """Filter a nested field name."""
    return {split[1] for s in field_name_set if (split := s.split(".", 1))[0] == field_name and len(split) > 1}


def _filter_nested_field_mapping(field_name_mapping: Mapping[str, str], field_name: str) -> dict[str, str]:
    """Filter a nested field name."""
    return {
        split[1]: v
        for s, v in field_name_mapping.items()
        if (split := s.split(".", 1))[0] == field_name and len(split) > 1
    }


def _create_msgspec_field(field_definition: TransferDTOFieldDefinition) -> Any:
    kwargs: dict[str, Any] = {}
    if field_definition.is_partial:
        kwargs["default"] = UNSET

    elif field_definition.default is not Empty:
        kwargs["default"] = field_definition.default

    elif field_definition.default_factory is not None:
        kwargs["default_factory"] = field_definition.default_factory

    if field_definition.serialization_name is not None:
        kwargs["name"] = field_definition.serialization_name

    return field(**kwargs)


def _create_struct_field_meta_for_field_definition(field_definition: TransferDTOFieldDefinition) -> msgspec.Meta | None:
    if (kwarg_definition := field_definition.kwarg_definition) is None or not isinstance(
        kwarg_definition, KwargDefinition
    ):
        return None

    return msgspec.Meta(
        description=kwarg_definition.description,
        examples=[e.value for e in kwarg_definition.examples or []],
        ge=kwarg_definition.ge,
        gt=kwarg_definition.gt,
        le=kwarg_definition.le,
        lt=kwarg_definition.lt,
        max_length=kwarg_definition.max_length if not field_definition.is_partial else None,
        min_length=kwarg_definition.min_length if not field_definition.is_partial else None,
        multiple_of=kwarg_definition.multiple_of,
        pattern=kwarg_definition.pattern,
        title=kwarg_definition.title,
    )


def _create_struct_for_field_definitions(
    *,
    model_name: str,
    module: str,
    field_definitions: tuple[TransferDTOFieldDefinition, ...],
    rename_strategy: RenameStrategy | dict[str, str] | None,
    forbid_unknown_fields: bool,
) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, type]] = []

    for field_definition in field_definitions:
        if field_definition.is_excluded:
            continue

        field_type = _create_transfer_model_type_annotation(field_definition.transfer_type)
        if field_definition.is_partial:
            field_type = Union[field_type, UnsetType]

        if field_definition.passthrough_constraints:
            if (field_meta := _create_struct_field_meta_for_field_definition(field_definition)) is not None:
                field_type = Annotated[field_type, field_meta]
        elif field_definition.kwarg_definition:
            field_type = Annotated[field_type, field_definition.kwarg_definition]

        struct_fields.append(
            (  # pyright: ignore[reportArgumentType]
                field_definition.name,
                field_type,
                _create_msgspec_field(field_definition),
            )
        )
    return defstruct(
        model_name,
        struct_fields,
        module=module,
        frozen=True,
        kw_only=True,
        rename=rename_strategy,
        forbid_unknown_fields=forbid_unknown_fields,
    )


def build_annotation_for_backend(
    model_type: type[Any], field_definition: FieldDefinition, transfer_model: type[Struct]
) -> Any:
    """A helper to re-build a generic outer type with new inner type.

    Args:
        model_type: The original model type.
        field_definition: The parsed type that represents the handler annotation for which the DTO is being applied.
        transfer_model: The transfer model generated to represent the model type.

    Returns:
        Annotation with new inner type if applicable.
    """
    if not field_definition.inner_types:
        if field_definition.is_subclass_of(model_type):
            return transfer_model
        return field_definition.annotation

    inner_types = tuple(
        build_annotation_for_backend(model_type, inner_type, transfer_model)
        for inner_type in field_definition.inner_types
    )

    return field_definition.safe_generic_origin[inner_types]


def _should_mark_private(field_definition: DTOFieldDefinition, underscore_fields_private: bool) -> bool:
    """Returns ``True`` where a field should be marked as private.

    Fields should be marked as private when:
    - the ``underscore_fields_private`` flag is set.
    - the field is not already marked.
    - the field name is prefixed with an underscore

    Args:
        field_definition: defined DTO field
        underscore_fields_private: whether fields prefixed with an underscore should be marked as private.
    """
    return bool(
        underscore_fields_private and field_definition.dto_field.mark is None and field_definition.name.startswith("_")
    )


def _should_exclude_field(
    field_definition: DTOFieldDefinition, exclude: Set[str], include: Set[str], is_data_field: bool
) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    Args:
        field_definition: defined DTO field
        exclude: names of fields to exclude
        include: names of fields to exclude
        is_data_field: whether the field is a data field

    Returns:
        ``True`` if the field should not be included in any data transfer.
    """
    field_name = field_definition.name
    if field_name in exclude:
        return True
    if include and field_name not in include and not (any(f.startswith(f"{field_name}.") for f in include)):
        return True
    if field_definition.dto_field.mark is Mark.PRIVATE:
        return True
    if is_data_field and field_definition.dto_field.mark is Mark.READ_ONLY:
        return True
    return not is_data_field and field_definition.dto_field.mark is Mark.WRITE_ONLY


def _create_transfer_model_type_annotation(transfer_type: TransferType) -> Any:
    """Create a type annotation for a transfer model.

    Uses the parsed type that originates from the data model and the transfer model generated to represent a nested
    type to reconstruct the type annotation for the transfer model.
    """
    if isinstance(transfer_type, SimpleType):
        if transfer_type.nested_field_info:
            return transfer_type.nested_field_info.model
        return transfer_type.field_definition.annotation

    if isinstance(transfer_type, CollectionType):
        return _create_transfer_model_collection_type(transfer_type)

    if isinstance(transfer_type, MappingType):
        return _create_transfer_model_mapping_type(transfer_type)

    if isinstance(transfer_type, TupleType):
        return _create_transfer_model_tuple_type(transfer_type)

    if isinstance(transfer_type, UnionType):
        return _create_transfer_model_union_type(transfer_type)

    raise RuntimeError(f"Unexpected transfer type: {type(transfer_type)}")


def _create_transfer_model_collection_type(transfer_type: CollectionType) -> Any:
    generic_collection_type = transfer_type.field_definition.safe_generic_origin
    inner_type = _create_transfer_model_type_annotation(transfer_type.inner_type)
    if transfer_type.field_definition.origin is tuple:
        return generic_collection_type[inner_type, ...]
    return generic_collection_type[inner_type]


def _create_transfer_model_tuple_type(transfer_type: TupleType) -> Any:
    inner_types = tuple(_create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def _create_transfer_model_union_type(transfer_type: UnionType) -> Any:
    inner_types = tuple(_create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def _create_transfer_model_mapping_type(transfer_type: MappingType) -> Any:
    key_type = _create_transfer_model_type_annotation(transfer_type.key_type)
    value_type = _create_transfer_model_type_annotation(transfer_type.value_type)
    return transfer_type.field_definition.safe_generic_origin[key_type, value_type]
