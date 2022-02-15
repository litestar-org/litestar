from functools import partial
from inspect import iscoroutinefunction, ismethod
from typing import Any, Optional

from anyio.to_thread import run_sync
from pydantic.fields import Undefined
from pydantic.typing import AnyCallable
from typing_extensions import Type

from starlite.signature import SignatureModel


class Provide:
    __slots__ = ("dependency", "use_cache", "value", "signature_model", "sync_to_thread")

    def __init__(self, dependency: AnyCallable, use_cache: bool = False, sync_to_thread: bool = False):
        self.dependency = dependency
        self.use_cache = use_cache
        self.value: Any = Undefined
        self.signature_model: Optional[Type[SignatureModel]] = None
        self.sync_to_thread = sync_to_thread
        if ismethod(dependency) and hasattr(dependency, "__self__"):
            # ensure that the method's self argument is preserved
            self.dependency = partial(dependency, dependency.__self__)

    async def __call__(self, **kwargs: Any) -> Any:
        """
        Proxies call to 'self.proxy'
        """

        if self.use_cache and self.value is not Undefined:
            return self.value
        fn = partial(self.dependency, **kwargs)
        if iscoroutinefunction(self.dependency):
            value = await fn()
        elif self.sync_to_thread:
            value = await run_sync(fn)
        else:
            value = fn()
        if self.use_cache:
            self.value = value
        return value

    def __eq__(self, other: Any) -> bool:
        # check if memory address is identical, otherwise compare attributes
        return other is self or (
            isinstance(other, self.__class__)
            and other.dependency == self.dependency
            and other.use_cache == self.use_cache
            and other.value == self.value
        )
