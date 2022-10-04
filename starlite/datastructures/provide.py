from typing import TYPE_CHECKING, Any, Optional, cast

from starlite.types import Empty
from starlite.utils.predicates import is_async_callable
from starlite.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from typing import Type

    from starlite.signature import SignatureModel
    from starlite.types import AnyCallable


class Provide:
    __slots__ = ("dependency", "use_cache", "value", "signature_model")

    def __init__(self, dependency: "AnyCallable", use_cache: bool = False, sync_to_thread: bool = False) -> None:
        """A wrapper class used for dependency injection.

        Args:
            dependency: Callable to inject, can be a function, method or class.
            use_cache: Cache the dependency return value. Defaults to False.
            sync_to_thread: Run sync code in an async thread. Defaults to False.
        """
        self.dependency = cast("AnyCallable", AsyncCallable(dependency) if sync_to_thread else dependency)
        self.use_cache = use_cache
        self.value: Any = Empty
        self.signature_model: Optional["Type[SignatureModel]"] = None

    async def __call__(self, **kwargs: Any) -> Any:
        """Proxies call to 'self.proxy'."""

        if self.use_cache and self.value is not Empty:
            return self.value

        if is_async_callable(self.dependency):
            value = await self.dependency(**kwargs)
        else:
            value = self.dependency(**kwargs)

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
