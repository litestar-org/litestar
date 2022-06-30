from typing import Any

from pydantic.fields import FieldInfo


def is_dependency_field(val: Any) -> bool:
    """
    Determine if a value is a `FieldInfo` instance created via the `Dependency()` function.

    Parameters
    ----------
    val : Any

    Returns
    -------
    bool
    """
    return isinstance(val, FieldInfo) and bool(val.extra.get("is_dependency"))
