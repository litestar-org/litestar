from typing import Any

from pydantic.fields import FieldInfo

from starlite.constants import EXTRA_KEY_IS_DEPENDENCY, EXTRA_KEY_SKIP_VALIDATION


def is_dependency_field(val: Any) -> bool:
    """Determine if a value is a `FieldInfo` instance created via the
    `Dependency()` function.

    Args:
        val(Any): value to be tested

    Returns:
        `True` if `val` is `FieldInfo` created by [`Dependency()`][starlite.params.Dependency] function.
    """
    return isinstance(val, FieldInfo) and bool(val.extra.get(EXTRA_KEY_IS_DEPENDENCY))


def should_skip_dependency_validation(val: Any) -> bool:
    """Determine if a value is a `FieldInfo` instance created via the
    `Dependency()` function set with ` skip_validation=True`.

    Args:
        val(Any): value to be tested

    Returns:
        `True` if `val` is `FieldInfo` created by [`Dependency()`][starlite.params.Dependency] function and
        `skip_validation=True` is set.
    """
    return is_dependency_field(val) and val.extra.get(EXTRA_KEY_SKIP_VALIDATION)
