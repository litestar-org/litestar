from typing import Any, cast


def get_name(value: Any) -> str:
    """Helper to get the '__name__' dunder of a value.

    Args:
        value: An arbitrary value.

    Returns:
        A name string.
    """

    if hasattr(value, "__name__"):
        return cast("str", value.__name__)
    return type(value).__name__
