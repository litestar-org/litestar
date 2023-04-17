from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, NewType, TypeVar
from uuid import uuid4

from msgspec import Struct, defstruct, field

from litestar.dto.factory.types import NestedFieldDefinition
from litestar.dto.factory.utils import get_model_type_hints
from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.serialization import decode_json, decode_msgpack
from litestar.types import Empty

from .abc import AbstractDTOBackend

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.connection import Request
    from litestar.dto.factory.types import FieldDefinition, FieldDefinitionsType
    from litestar.types.serialization import LitestarEncodableType
    from litestar.utils.signature import ParsedType

__all__ = ["MsgspecDTOBackend"]


MsgspecField = NewType("MsgspecField", type)
StructT = TypeVar("StructT", bound=Struct)
T = TypeVar("T")


class MsgspecDTOBackend(AbstractDTOBackend[Struct]):
    __slots__ = ()

    def parse_raw(self, raw: bytes, media_type: MediaType | str) -> Struct | Collection[Struct]:
        if media_type == MediaType.JSON:
            transfer_data = decode_json(raw, type_=self.annotation)
        elif media_type == MediaType.MESSAGEPACK:
            transfer_data = decode_msgpack(raw, type_=self.annotation)
        else:
            raise SerializationException(f"Unsupported media type: '{media_type}'")
        return transfer_data  # type:ignore[return-value]

    def populate_data_from_raw(self, model_type: type[T], raw: bytes, media_type: MediaType | str) -> T | Collection[T]:
        parsed_data = self.parse_raw(raw, media_type)
        return _build_data_from_struct(model_type, parsed_data, self.field_definitions)

    def encode_data(self, data: Any, connection: Request) -> LitestarEncodableType:
        if isinstance(data, CollectionsCollection):
            return self.parsed_type.origin(  # type:ignore[no-any-return]
                _build_struct_from_model(datum, self.data_container_type) for datum in data  # pyright:ignore
            )
        return _build_struct_from_model(data, self.data_container_type)

    @classmethod
    def from_field_definitions(cls, annotation: Any, field_definitions: FieldDefinitionsType) -> Any:
        return cls(
            annotation, _create_msgspec_struct_for_field_definitions(str(uuid4()), field_definitions), field_definitions
        )


def _create_msgspec_field(field_definition: FieldDefinition) -> MsgspecField | None:
    kws: dict[str, Any] = {}
    if field_definition.default is not Empty:
        kws["default"] = field_definition.default

    if field_definition.default_factory is not Empty:
        kws["default_factory"] = field_definition.default_factory

    if not kws:
        return None

    return field(**kws)  # type:ignore[no-any-return]


def _create_struct_field_def(
    name: str, type_: type[Any], field_: MsgspecField | None
) -> tuple[str, type[Any]] | tuple[str, type[Any], MsgspecField]:
    if field_ is None:
        return name, type_
    return name, type_, field_


def _create_msgspec_struct_for_field_definitions(
    model_name: str, field_definitions: FieldDefinitionsType
) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, MsgspecField]] = []
    for k, v in field_definitions.items():
        if isinstance(v, NestedFieldDefinition):
            nested_struct = _create_msgspec_struct_for_field_definitions(
                f"{model_name}.{k}", v.nested_field_definitions
            )
            struct_fields.append(
                _create_struct_field_def(k, v.make_field_type(nested_struct), _create_msgspec_field(v.field_definition))
            )
        else:
            struct_fields.append(_create_struct_field_def(k, v.parsed_type.annotation, _create_msgspec_field(v)))
    return defstruct(model_name, struct_fields, frozen=True, kw_only=True)


def _build_model_from_struct(model_type: type[T], data: Struct, field_definitions: FieldDefinitionsType) -> T:
    """Create instance of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    unstructured_data = {}
    for k in data.__slots__:  # type:ignore[attr-defined]
        v = getattr(data, k)

        field = field_definitions[k]

        if isinstance(field, NestedFieldDefinition) and isinstance(v, CollectionsCollection):
            parsed_type = field.field_definition.parsed_type
            if parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")
            unstructured_data[k] = parsed_type.origin(
                _build_model_from_struct(field.nested_type, item, field.nested_field_definitions) for item in v
            )
        elif isinstance(field, NestedFieldDefinition) and isinstance(v, Struct):
            unstructured_data[k] = _build_model_from_struct(field.nested_type, v, field.nested_field_definitions)
        else:
            unstructured_data[k] = v

    return model_type(**unstructured_data)


def _build_data_from_struct(
    model_type: type[T], data: Struct | Collection[Struct], field_definitions: FieldDefinitionsType
) -> T | Collection[T]:
    """Create instance or iterable of instances of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    if isinstance(data, CollectionsCollection):
        return type(data)(  # type:ignore[return-value]
            _build_data_from_struct(model_type, item, field_definitions) for item in data  # type:ignore[call-arg]
        )
    return _build_model_from_struct(model_type, data, field_definitions)


def _build_struct_from_model(model: Any, struct_type: type[StructT]) -> StructT:
    """Convert ``model`` to instance of ``struct_type``

    It is expected that attributes of ``struct_type`` are a subset of the attributes of ``model``.

    Args:
        model: a model instance
        struct_type: a subclass of ``msgspec.Struct``

    Returns:
        Instance of ``struct_type``.
    """
    data = {}
    for key, parsed_type in get_model_type_hints(struct_type).items():
        model_val = getattr(model, key)
        if parsed_type.is_subclass_of(Struct):
            data[key] = _build_struct_from_model(model_val, parsed_type.annotation)
        elif parsed_type.is_union:
            data[key] = _handle_union_type(parsed_type, model_val)
        elif parsed_type.is_collection:
            data[key] = _handle_collection_type(parsed_type, model_val)
        else:
            data[key] = model_val
    return struct_type(**data)


def _handle_union_type(parsed_type: ParsedType, model_val: Any) -> Any:
    """Handle union type.

    Args:
        parsed_type: Parsed type.
        model_val: Model value.

    Returns:
        Model value.
    """
    for inner_type in parsed_type.inner_types:
        if inner_type.is_subclass_of(Struct):
            # If there are multiple struct inner types, we use the first one that creates without exception.
            # This is suboptimal, and perhaps can be improved by assigning the model that the inner struct
            # was derived upon to the struct itself, which would allow us to isolate the correct struct to use
            # for the nested model type instance. For the most likely case of an optional union of a single
            # nested type, this should be sufficient.
            try:
                return _build_struct_from_model(model_val, inner_type.annotation)
            except (AttributeError, TypeError):
                continue
    return model_val


def _handle_collection_type(parsed_type: ParsedType, model_val: Any) -> Any:
    """Handle collection type.

    Args:
        parsed_type: Parsed type.
        model_val: Model value.

    Returns:
        Model value.
    """
    if parsed_type.inner_types and (inner_type := parsed_type.inner_types[0]).is_subclass_of(Struct):
        return parsed_type.origin(_build_struct_from_model(m, inner_type.annotation) for m in model_val)
    return model_val
