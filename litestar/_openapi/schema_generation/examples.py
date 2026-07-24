from __future__ import annotations

import typing
from dataclasses import replace
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, get_args

import msgspec
from polyfactory.exceptions import ParameterException
from polyfactory.factories import DataclassFactory
from polyfactory.field_meta import FieldMeta, Null
from polyfactory.utils.helpers import unwrap_annotation
from polyfactory.utils.predicates import is_union

from litestar.openapi.spec import Example
from litestar.plugins.pydantic.utils import is_pydantic_model_instance
from litestar.types import Empty
from litestar.typing import TypeAliasTypes

if TYPE_CHECKING:
    from litestar.typing import FieldDefinition


class ExampleFactory(DataclassFactory[Example]):
    __model__ = Example
    __random_seed__ = 10
    __check_model__ = False


def _normalize_example_value(value: Any) -> Any:
    """Normalize the example value to make it look a bit prettier."""
    # if UnsetType is part of the union, then it might get chosen as the value
    # but that will not be properly serialized by msgspec unless it is for a field
    # in a msgspec Struct
    if is_union(value):
        args = list(get_args(value))
        try:
            args.remove(msgspec.UnsetType)
            value = typing.Union[tuple(args)]
        except ValueError:
            # UnsetType not part of the Union
            pass

    value = unwrap_annotation(annotation=value)
    if isinstance(value, (Decimal, float)):
        value = round(float(value), 2)
    if isinstance(value, Enum):
        value = value.value
    if is_pydantic_model_instance(value):
        from litestar.plugins.pydantic import _model_dump

        value = _model_dump(value)
    if isinstance(value, (list, set)):
        value = [_normalize_example_value(v) for v in value]
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = _normalize_example_value(v)
    return value


def _type_alias_is_recursive(alias: Any) -> bool:
    """Return whether expanding ``alias`` would recurse, i.e. the alias is reachable from its own value.

    This covers both directly self-referential aliases (``type JSON = ... | list[JSON]``) and mutually
    recursive ones (``type A = B`` / ``type B = A``), where ``alias`` is reached again via another alias.
    """
    target = id(alias)
    seen: set[int] = set()
    stack = [alias.__value__]
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        if isinstance(obj, TypeAliasTypes):
            if id(obj) == target:
                return True
            stack.append(obj.__value__)
        stack.extend(get_args(obj))
    return False


def _contains_recursive_type_alias(annotation: Any) -> bool:
    """Return whether ``annotation`` is, or contains, a self-referential PEP 695 ``type`` alias.

    The example factory does not guard against recursive ``type`` aliases (it does for recursive models) and
    would recurse without bound while building an example value for one, e.g. ``dict[str, JSON]`` where
    ``type JSON = ... | dict[str, JSON]``. This detects such aliases so example generation can be skipped.
    A non-recursive alias reused several times in one annotation (``tuple[Name, Name]``) is *not* flagged.
    """
    seen: set[int] = set()
    stack = [annotation]
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        if isinstance(obj, TypeAliasTypes):
            if _type_alias_is_recursive(obj):
                return True
            stack.append(obj.__value__)
        stack.extend(get_args(obj))
    return False


def _create_field_meta(field: FieldDefinition) -> FieldMeta:
    return FieldMeta.from_type(
        annotation=field.annotation,
        default=field.default if field.default is not Empty else Null,
        name=field.name,
    )


def create_examples_for_field(field: FieldDefinition) -> list[Example]:
    """Create an OpenAPI Example instance.

    Args:
        field: A signature field.

    Returns:
        A list including a single example.
    """
    if _contains_recursive_type_alias(field.annotation):
        # the example factory would recurse without bound on a self-referential ``type`` alias
        return []
    try:
        field_meta = _create_field_meta(replace(field, annotation=_normalize_example_value(field.annotation)))
        value = ExampleFactory.get_field_value(field_meta)
        return [Example(description=f"Example {field.name} value", value=value)]
    except ParameterException:
        return []
