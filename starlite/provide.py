from functools import partial
from inspect import ismethod
from typing import Any, Callable

from pydantic.fields import Undefined


class Provide:
    __slots__ = ("dependency", "use_cache", "value", "identifier")

    def __init__(self, dependency: Callable, use_cache: bool = False):
        self.dependency = dependency
        self.use_cache = use_cache
        self.value = Undefined
        if ismethod(dependency) and hasattr(dependency, "__self__"):
            # ensure that the method's self argument is preserved
            self.dependency = partial(dependency, dependency.__self__)  # type: ignore

    def __call__(self, **kwargs) -> Any:
        """
        Proxies call to 'self.proxy'
        """

        if self.use_cache and self.value is not Undefined:
            return self.value
        value = self.dependency(**kwargs)
        if self.use_cache:
            self.value = value
        return value

    def __eq__(self, other):
        # check if memory address is identical, otherwise compare attributes
        return other is self or (
            isinstance(other, self.__class__)
            and other.dependency == self.dependency
            and other.use_cache == self.use_cache
            and other.value == self.value
        )
