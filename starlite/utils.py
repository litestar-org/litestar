from types import GenericAlias
from typing import Any, Callable, Optional


class cached_property:  # pylint: disable=invalid-name
    """
    decorator that can be used in all versions of python (unlike functools.cached_property)
    """

    __class_getitem__ = classmethod(GenericAlias)

    def __init__(self, method: Callable):
        self.method = method
        self.attribute_name: Optional[str] = None
        self.__doc__ = method.__doc__

    def __set_name__(self, owner: Any, name: str):
        self.attribute_name = name

    def __get__(self, class_instance: Any, owner=None):
        if class_instance is None:
            return self
        try:
            value = class_instance.__dict__.get(self.attribute_name)
            if value:
                return value
            value = class_instance.__dict__[self.attribute_name] = self.method(class_instance)
            return value
        except (AttributeError, ValueError) as e:  # pragma: no cover
            raise TypeError(
                f"Cannot retrieve or set cached value for {self.attribute_name!r}. "
                f"Either __set_name__ has not been called or the class "
                f"{class_instance.__class__.__name__} does not support the __dict__ method"
            ) from e
