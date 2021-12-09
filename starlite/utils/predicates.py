from inspect import isfunction, ismethod
from typing import Any, Callable


def is_function_or_method(value: Callable) -> bool:
    """
    Return True if value is a method or function, False for other callables
    """
    return isfunction(value) or ismethod(value)


def is_route_handler_function(value: Any) -> bool:
    """
    Return True if value is a RouteHandlerFunction, False for other callables
    """
    return is_function_or_method(value) and hasattr(value, "route_info")
