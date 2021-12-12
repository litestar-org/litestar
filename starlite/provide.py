from functools import partial
from inspect import ismethod
from typing import Any, Callable


class Provide:
    __slots__ = ("dependency", "use_cache", "value")

    def __init__(self, dependency: Callable, use_cache: bool = False):
        self.dependency = dependency
        self.use_cache = use_cache
        self.value = None
        if ismethod(dependency) and hasattr(dependency, "__self__"):
            # ensure that the method's self argument is preserved
            self.dependency = partial(dependency, dependency.__self__)  # type: ignore

    def __call__(self, **kwargs) -> Any:
        """
        Proxies call to 'self.proxy'
        """

        if self.use_cache and self.value:
            return self.value
        value = self.dependency(**kwargs)
        if self.use_cache:
            self.value = value
        return value
