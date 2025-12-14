from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, NamedTuple, get_args, get_origin

import typing_extensions

from litestar.plugins import OpenAPISchemaPlugin
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.openapi.spec import Schema


class _TypedDictInfo(NamedTuple):
    required_keys: frozenset[str]
    optional_keys: frozenset[str]
    readonly_keys: frozenset[str]
    mutable_keys: frozenset[str]


def _get_typed_dict_info(tp: Any) -> _TypedDictInfo:
    if sys.version_info < (3, 9):
        return _make_typed_dict_info(tp)

    return _TypedDictInfo(
        required_keys=tp.__required_keys__,
        optional_keys=tp.__optional_keys__,
        readonly_keys=getattr(tp, "__readonly_keys__", frozenset()),
        mutable_keys=getattr(tp, "__mutable_keys__", frozenset()),
    )


# backport of the 3.9+ logic to extract TypedDict information
def _get_typeddict_qualifiers(annotation_type: Any) -> Any:
    while True:
        annotation_origin = get_origin(annotation_type)
        if annotation_origin is typing_extensions.Annotated:
            annotation_args = get_args(annotation_type)
            if annotation_args:
                annotation_type = annotation_args[0]
            else:
                break
        elif annotation_origin is typing_extensions.Required:
            yield typing_extensions.Required
            (annotation_type,) = get_args(annotation_type)
        elif annotation_origin is typing_extensions.NotRequired:
            yield typing_extensions.NotRequired
            (annotation_type,) = get_args(annotation_type)
        elif annotation_origin is typing_extensions.ReadOnly:
            yield typing_extensions.ReadOnly
            (annotation_type,) = get_args(annotation_type)
        else:
            break


def _make_typed_dict_info(tp: Any) -> _TypedDictInfo:
    required_keys: set[str] = set()
    optional_keys: set[str] = set()
    readonly_keys: set[str] = set()
    mutable_keys: set[str] = set()
    bases = tp.mro()

    annotations = {}
    own_annotations = getattr(tp, "__annotations__", {})

    for base in bases:
        annotations.update(base.__dict__.get("__annotations__", {}))

        base_required = base.__dict__.get("__required_keys__", set())
        required_keys |= base_required
        optional_keys -= base_required

        base_optional = base.__dict__.get("__optional_keys__", set())
        required_keys -= base_optional
        optional_keys |= base_optional

        readonly_keys.update(base.__dict__.get("__readonly_keys__", ()))
        mutable_keys.update(base.__dict__.get("__mutable_keys__", ()))

    annotations.update(own_annotations)
    for annotation_key, annotation_type in own_annotations.items():
        qualifiers = set(_get_typeddict_qualifiers(annotation_type))
        if typing_extensions.Required in qualifiers:
            is_required = True
        elif typing_extensions.NotRequired in qualifiers:
            is_required = False
        else:
            is_required = tp.__total__

        if is_required:
            required_keys.add(annotation_key)
            optional_keys.discard(annotation_key)
        else:
            optional_keys.add(annotation_key)
            required_keys.discard(annotation_key)

        if typing_extensions.ReadOnly in qualifiers:
            if annotation_key in mutable_keys:
                raise TypeError(f"Cannot override mutable key {annotation_key!r} with read-only key")
            readonly_keys.add(annotation_key)
        else:
            mutable_keys.add(annotation_key)
            readonly_keys.discard(annotation_key)

    return _TypedDictInfo(
        frozenset(required_keys),
        frozenset(optional_keys),
        frozenset(readonly_keys),
        frozenset(mutable_keys),
    )


class TypedDictSchemaPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.is_typeddict_type

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        type_hints = field_definition.get_type_hints(include_extras=True, resolve_generics=True)

        info = _get_typed_dict_info(field_definition.type_)

        return schema_creator.create_component_schema(
            field_definition,
            required=sorted(info.required_keys),
            property_fields={k: FieldDefinition.from_kwarg(v, k) for k, v in type_hints.items()},
        )
