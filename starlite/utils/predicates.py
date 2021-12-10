from inspect import isfunction, ismethod
from typing import Callable


def is_function_or_method(value: Callable) -> bool:
    """
    Return True if value is a method or function, False for other callables
    """
    return isfunction(value) or ismethod(value)
