from __future__ import annotations

from dataclasses import Field, fields
from typing import TYPE_CHECKING

from litestar.types import Empty
from litestar.types.protocols import DataclassProtocol

if TYPE_CHECKING:
    from typing import AbstractSet, Any, Iterable

__all__ = (
    "extract_dataclass_fields",
    "extract_dataclass_items",
    "simple_asdict",
)


def extract_dataclass_fields(
    dt: DataclassProtocol,
    exclude_none: bool = False,
    exclude_empty: bool = False,
    include: AbstractSet[str] | None = None,
    exclude: AbstractSet[str] | None = None,
) -> tuple[Field, ...]:
    """Extract dataclass fields.

    Args:
        dt: A dataclass instance.
        exclude_none: Whether to exclude None values.
        exclude_empty: Whether to exclude Empty values.
        include: An iterable of fields to include.
        exclude: An iterable of fields to exclude.


    Returns:
        A tuple of dataclass fields.
    """
    include = include or set()
    exclude = exclude or set()

    if common := (include & exclude):
        raise ValueError(f"Fields {common} are both included and excluded.")

    dataclass_fields: Iterable[Field] = fields(dt)
    if exclude_none:
        dataclass_fields = (field for field in dataclass_fields if getattr(dt, field.name) is not None)
    if exclude_empty:
        dataclass_fields = (field for field in dataclass_fields if getattr(dt, field.name) is not Empty)
    if include:
        dataclass_fields = (field for field in dataclass_fields if field.name in include)
    if exclude:
        dataclass_fields = (field for field in dataclass_fields if field.name not in exclude)

    return tuple(dataclass_fields)


def extract_dataclass_items(
    dt: DataclassProtocol,
    exclude_none: bool = False,
    exclude_empty: bool = False,
    include: AbstractSet[str] | None = None,
    exclude: AbstractSet[str] | None = None,
) -> tuple[tuple[str, Any], ...]:
    """Extract dataclass name, value pairs.

    Unlike the 'asdict' method exports by the stlib, this function does not pickle values.

    Args:
        dt: A dataclass instance.
        exclude_none: Whether to exclude None values.
        exclude_empty: Whether to exclude Empty values.
        include: An iterable of fields to include.
        exclude: An iterable of fields to exclude.

    Returns:
        A tuple of key/value pairs.
    """
    dataclass_fields = extract_dataclass_fields(dt, exclude_none, exclude_empty, include, exclude)
    return tuple((field.name, getattr(dt, field.name)) for field in dataclass_fields)


def simple_asdict(
    obj: DataclassProtocol,
    exclude_none: bool = False,
    exclude_empty: bool = False,
    by_alias: bool = False,
    exclude: set | None = None,
) -> dict[str, Any]:
    """Convert a dataclass to a dictionary.

    This method has important differences to the standard library version:
    - it does not deepcopy values
    - it does not recurse into collections

    Args:
        obj: A dataclass instance.
        exclude_none: Whether to exclude None values.
        exclude_empty: Whether to exclude Empty values.
        by_alias: Whether to use alias for the field name.
        exclude: Name of attributes to be excluded.

    Returns:
        A dictionary of key/value pairs.
    """
    ret = {}
    for field in extract_dataclass_fields(obj, exclude_none, exclude_empty, exclude=exclude):
        field_name = field.name if not by_alias else "-".join(field.name.split("_"))
        value = getattr(obj, field.name)
        if isinstance(value, DataclassProtocol):
            ret[field_name] = simple_asdict(value, exclude_none, exclude_empty)
        else:
            ret[field_name] = getattr(obj, field.name)
    return ret
