from __future__ import annotations

from dataclasses import asdict, fields
from typing import TYPE_CHECKING, cast

from starlite.types import DataclassProtocol, Empty

if TYPE_CHECKING:
    from typing import Any, Iterable

__all__ = (
    "asdict_filter_empty",
    "extract_dataclass_fields",
)


def extract_dataclass_fields(
    dt: Any, exclude_none: bool = False, include: Iterable[str] | None = None
) -> tuple[tuple[str, Any], ...]:
    """Extract dataclass fields. Unlike the 'asdict' method exports by the stlib, this function does not pickle values.

    Args:
        dt: A dataclass instance.
        exclude_none: Whether to exclude None values.
        include: An iterable of fields to include.

    Returns:
        A tuple of key/value pairs.
    """
    return tuple(
        (field_name, getattr(dt, field_name))
        for field_name in cast("DataclassProtocol", dt).__dataclass_fields__
        if (not exclude_none or getattr(dt, field_name) is not None)
        and ((include is not None and field_name in include) or include is None)
    )


def asdict_filter_empty(obj: DataclassProtocol) -> dict[str, Any]:
    """Same as stdlib's ``dataclasses.asdict`` with additional filtering for :class:`Empty<.types.Empty>`.

    Args:
        obj: A dataclass instance.

    Returns:
        ``obj`` converted into a ``dict`` of its fields, with any :class:`Empty<.types.Empty>` values excluded.
    """
    return {k: v for k, v in asdict(obj).items() if v is not Empty}


def simple_asdict(obj: DataclassProtocol) -> dict[str, Any]:
    """Recursively convert a dataclass instance into a ``dict`` of its fields, without using ``copy.deepcopy()``.

    The standard library ``dataclasses.asdict()`` function uses ``copy.deepcopy()`` on any value that is not a
    dataclass, dict, list or tuple, which presents a problem when the dataclass holds items that cannot be pickled.

    This function provides an alternative that does not use ``copy.deepcopy()``, and is a much simpler implementation,
    only recursing into other dataclasses.

    Args:
        obj: A dataclass instance.

    Returns:
        ``obj`` converted into a ``dict`` of its fields.
    """
    field_values = ((field.name, getattr(obj, field.name)) for field in fields(obj))
    return {k: simple_asdict(v) if isinstance(v, DataclassProtocol) else v for k, v in field_values}


def simple_asdict_filter_empty(obj: DataclassProtocol) -> dict[str, Any]:
    """Same as asdict_filter_empty but uses ``simple_asdict``.

    Args:
        obj: A dataclass instance.

    Returns:
        ``obj`` converted into a ``dict`` of its fields, with any :class:`Empty<.types.Empty>` values excluded.
    """
    return {k: v for k, v in simple_asdict(obj).items() if v is not Empty}
