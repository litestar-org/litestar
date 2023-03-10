from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, cast

__all__ = ("extract_dataclass_fields",)


if TYPE_CHECKING:
    from starlite.types import DataclassProtocol


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
