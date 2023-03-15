from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from dataclasses import MISSING, Field, fields
from inspect import getmodule
from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import Self, get_args, get_origin, get_type_hints

from starlite.dto import AbstractDTO, DTOField, Purpose
from starlite.dto.backends.msgspec import MsgspecDTOBackend
from starlite.dto.config import DTO_FIELD_META_KEY
from starlite.dto.types import FieldDefinition, NestedFieldDefinition
from starlite.enums import MediaType
from starlite.serialization import decode_json, encode_json

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from msgspec import Struct

    from starlite.dto.types import FieldDefinitionsType
    from starlite.types import DataclassProtocol


__all__ = ("DataclassDTO", "ModelT")

ModelT = TypeVar("ModelT", bound="DataclassProtocol")
AnyDataclass = TypeVar("AnyDataclass", bound="DataclassProtocol")


class DataclassDTO(AbstractDTO[ModelT], Generic[ModelT]):
    """Support for domain modelling with dataclasses."""

    dto_backend_type = MsgspecDTOBackend
    dto_backend: ClassVar[MsgspecDTOBackend]

    @classmethod
    def parse_model(
        cls, model_type: type[DataclassProtocol], nested_depth: int = 0, recursive_depth: int = 0
    ) -> FieldDefinitionsType:
        defined_fields: dict[str, FieldDefinition | NestedFieldDefinition] = {}
        dc_fields = {f.name: f for f in fields(model_type)}
        for key, type_hint in get_type_hints(model_type, localns=_get_localns(model_type)).items():
            if not (dc_field := dc_fields.get(key)):
                continue

            dto_field = _get_dto_field(dc_field)

            if cls.should_exclude_field(key, type_hint, dto_field):
                continue

            field_definition = FieldDefinition(field_type=type_hint)
            if cls.config.purpose is not Purpose.READ:
                set_field_definition_default(field_definition, dc_field)

            if cls._detect_nested(type_hint):
                nested_field_definition = cls._handle_nested(field_definition, nested_depth, recursive_depth)
                if nested_field_definition is not None:
                    defined_fields[key] = nested_field_definition
                continue

            defined_fields[key] = field_definition
        return defined_fields

    @classmethod
    def _detect_nested(cls, field_type: type) -> bool:
        args = get_args(field_type)
        if not args:
            return hasattr(field_type, "__dataclass_fields__")
        return any(hasattr(a, "__dataclass_fields__") for a in args)

    @classmethod
    def _handle_nested(
        cls, field_definition: FieldDefinition, nested_depth: int, recursive_depth: int
    ) -> NestedFieldDefinition | None:
        if nested_depth == cls.config.max_nested_depth:
            return None

        args = get_args(field_definition.field_type)
        origin = get_origin(field_definition.field_type)
        nested = NestedFieldDefinition(
            field_definition=field_definition,
            origin=origin,
            args=args,
            nested_type=args[0] if args else field_definition.field_type,
        )

        if (is_recursive := nested.is_recursive(cls.model_type)) and recursive_depth == cls.config.max_nested_recursion:
            return None

        nested.nested_field_definitions = cls.parse_model(
            nested.nested_type, nested_depth + 1, recursive_depth + is_recursive
        )
        return nested

    @classmethod
    def from_bytes(cls, raw: bytes, media_type: MediaType | str = MediaType.JSON) -> Self:
        parsed = cls.dto_backend.raw_to_dict(raw, media_type)
        return cls(data=cls._build(cls.model_type, parsed, cls.field_definitions))

    def to_encodable_type(self, media_type: str | MediaType) -> Struct:
        return decode_json(encode_json(self.data), self.dto_backend.model)

    @classmethod
    def _build(
        cls, model_type: type[AnyDataclass], data: MutableMapping[str, Any], field_definitions: FieldDefinitionsType
    ) -> AnyDataclass:
        """Create an instance of `model_type`.

        Fill the bound dataclass recursively with values from the serde instance.
        """
        for k, v in data.items():
            field_definition = field_definitions[k]
            if isinstance(field_definition, FieldDefinition):
                continue

            if isinstance(v, MutableMapping):
                data[k] = cls._build(field_definition.nested_type, v, field_definition.nested_field_definitions)
            elif isinstance(v, Iterable):
                if field_definition.origin is None:
                    raise RuntimeError("Unexpected origin value for collection type.")
                data[k] = field_definition.origin(
                    cls._build(field_definition.nested_type, item, field_definition.nested_field_definitions)
                    for item in v
                )

        return model_type(**data)


def set_field_definition_default(field_definition: FieldDefinition, dc_field: Field) -> None:
    if dc_field.default is not MISSING:
        field_definition.default = dc_field.default

    if dc_field.default_factory is not MISSING:
        field_definition.default_factory = dc_field.default_factory


def _get_dto_field(dc_field: Field) -> DTOField:
    return dc_field.metadata.get(DTO_FIELD_META_KEY, DTOField())


def _get_localns(model: type[DataclassProtocol]) -> dict[str, Any]:
    model_module = getmodule(model)
    return vars(model_module) if model_module is not None else {}
