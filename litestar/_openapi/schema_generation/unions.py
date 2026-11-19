import itertools
import json
from collections.abc import Mapping
from typing import Any, NamedTuple

from litestar.openapi.spec import OpenAPIType, Reference, Schema

__all__ = ("use_any_of_if_overlapping",)

_COMPONENT_PREFIX = "#/components/schemas/"


class _Shape(NamedTuple):
    types: frozenset[OpenAPIType]
    values: frozenset[str] | None = None
    tags: frozenset[tuple[str, str]] = frozenset()


def _value_key(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return json.dumps(value, sort_keys=True, default=str)


def _get_shape(
    value: Schema | Reference, components: Mapping[str, Schema], resolving: frozenset[str] = frozenset()
) -> _Shape | None:
    """Return the JSON types a schema accepts, the values it is restricted to, if any, and its tags: the required
    properties of an object that only accept one value.

    ``None`` means the schema can't be summarised this way and may accept any value.
    """
    if isinstance(value, Reference):
        name = value.ref.removeprefix(_COMPONENT_PREFIX)
        if name in resolving or (component := components.get(name)) is None:
            return None
        return _get_shape(component, components, resolving | {name})
    if value.all_of:
        return _get_shape(value.all_of[0], components, resolving) if len(value.all_of) == 1 else None
    if members := value.one_of or value.any_of:
        shapes = [_get_shape(member, components, resolving) for member in members]
        if any(shape is None for shape in shapes):
            return None
        types = frozenset().union(*(shape.types for shape in shapes if shape))
        values = [shape.values for shape in shapes if shape]
        return _Shape(types, None if any(v is None for v in values) else frozenset().union(*(v for v in values if v)))
    if value.type is None:
        return None
    types = frozenset((value.type,) if isinstance(value.type, OpenAPIType) else value.type)
    if value.const is not None:
        return _Shape(types, frozenset((_value_key(value.const),)))
    if value.enum:
        return _Shape(types, frozenset(map(_value_key, value.enum)))
    return _Shape(types, tags=_get_tags(value, components, resolving))


def _get_tags(value: Schema, components: Mapping[str, Schema], resolving: frozenset[str]) -> frozenset[tuple[str, str]]:
    tags: set[tuple[str, str]] = set()
    for name in value.required or ():
        if (
            (schema := (value.properties or {}).get(name)) is not None
            and (shape := _get_shape(schema, components, resolving)) is not None
            and shape.values is not None
            and len(shape.values) == 1
        ):
            tags.add((name, next(iter(shape.values))))
    return frozenset(tags)


def _overlap(first: _Shape, second: _Shape) -> bool:
    (first_types, first_values, first_tags), (second_types, second_values, second_tags) = first, second
    if first_values is not None and second_values is not None:
        return not first_values.isdisjoint(second_values)
    second_tag_values = dict(second_tags)
    if any(second_tag_values.get(name, tag_value) != tag_value for name, tag_value in first_tags):
        return False
    if OpenAPIType.NUMBER in first_types:
        first_types |= {OpenAPIType.INTEGER}
    if OpenAPIType.NUMBER in second_types:
        second_types |= {OpenAPIType.INTEGER}
    return not first_types.isdisjoint(second_types)


def use_any_of_if_overlapping(schema: Schema, components: Mapping[str, Schema]) -> None:
    """Turn the ``oneOf`` of ``schema`` into an ``anyOf`` if its members may accept the same value.

    A value must match exactly one member of a ``oneOf``, so a ``oneOf`` is only kept if its members accept disjoint
    sets of values, judged by their JSON types, their ``enum`` or ``const`` values and the single values their
    required properties accept. ``integer`` overlaps ``number``. A ``oneOf`` with a ``discriminator`` is left as
    declared.
    """
    members = schema.one_of
    if members is None or len(members) < 2 or schema.any_of is not None or schema.discriminator is not None:
        return
    shapes = [_get_shape(member, components) for member in members]
    if any(shape is None for shape in shapes) or any(
        _overlap(first, second) for first, second in itertools.combinations((shape for shape in shapes if shape), 2)
    ):
        schema.any_of, schema.one_of = members, None
